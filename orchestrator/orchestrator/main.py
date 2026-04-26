"""Orchestrator main loop - dispatches tasks to agents and enforces gates."""
import json
import os
import shlex
import signal
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict

from .task_queue import TaskQueue
from .budget import BudgetEnforcer
from .gate import GateValidator, GateStatus
from .worktree import WorktreeManager


@dataclass
class AgentSession:
    """Tracks an active agent session."""
    feature_id: str
    task_id: int
    current_agent: str
    tmux_session: str
    repo: str = "falara"
    github_repo: str = "borisdeluxe/falara"
    started_at: Optional[str] = None


class Orchestrator:
    """Main orchestrator loop - dispatches tasks and enforces gates."""

    AGENT_SEQUENCE = [
        "concept_clarifier",
        "architect_planner",
        "test_designer",
        "implementer",
        "security_reviewer",
        "refactorer",
        "qa_validator",
        "docs_updater",
        "deploy_runner",
    ]

    REVIEW_ENTRY_POINT = "security_reviewer"

    AGENT_OUTPUT_ARTIFACTS = {
        "concept_clarifier": "tk-draft.md",
        "architect_planner": "plan.md",
        "test_designer": "test-plan.md",
        "implementer": "implementation.md",
        "security_reviewer": "security-report.md",
        "refactorer": "refactor-report.md",
        "qa_validator": "qa-report.md",
        "docs_updater": "docs-report.md",
        "deploy_runner": "deploy-log.md",
    }

    def __init__(
        self,
        db,
        pipeline_dir: Optional[Path] = None,
        worktree_dir: Optional[Path] = None,
        repos_dir: Optional[Path] = None,
        github_token: Optional[str] = None,
    ):
        self.db = db
        self.task_queue = TaskQueue(db)
        self.budget = BudgetEnforcer(db)
        self.gate = GateValidator(db)

        self.pipeline_dir = pipeline_dir or Path("/opt/agency/.pipeline")
        self.worktree_dir = worktree_dir or Path("/opt/agency/worktrees")
        self.repos_dir = repos_dir or Path("/opt/agency/repos")
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")

        self.pipeline_dir.mkdir(parents=True, exist_ok=True)
        self.worktree_dir.mkdir(parents=True, exist_ok=True)

        self._worktree_managers: Dict[str, WorktreeManager] = {}
        self._active_sessions: Dict[str, AgentSession] = {}
        self._shutdown_requested = False
        self._kill_sessions_on_shutdown = False

    def _get_repo_dir(self, repo_name: str) -> Path:
        """Get the repo directory for a given repo name.

        Looks up the path from the agency_repos table first.
        Falls back to legacy hardcoded paths when not found in DB.
        """
        try:
            row = self.db.execute(
                "SELECT path FROM agency_repos WHERE name = %s",
                (repo_name,)
            ).fetchone()

            if row and row.get("path"):
                return Path(row["path"])

            # Fallback for legacy names not yet in agency_repos
            if repo_name == "frontend":
                return Path("/opt/agency/repos/falara-frontend")

        except Exception as e:
            print(f"Warning: Could not lookup repo '{repo_name}' in agency_repos: {e}")

        # Default fallback: repos_dir / repo_name
        return self.repos_dir / repo_name

    def get_worktree_manager(self, repo: str, github_repo: str) -> WorktreeManager:
        """Get or create WorktreeManager for a specific repo."""
        if repo not in self._worktree_managers:
            self._worktree_managers[repo] = WorktreeManager(
                repo_dir=self._get_repo_dir(repo),
                worktree_dir=self.worktree_dir,
                github_token=self.github_token,
                github_repo=github_repo,
            )
        return self._worktree_managers[repo]

    def process_one(self) -> bool:
        """Process one pending task. Returns True if a task was processed."""
        task = self.task_queue.fetch_pending()
        if task is None:
            return False

        budget_check = self.budget.can_spend(task.feature_id, amount=0.50)
        if not budget_check.allowed:
            self.task_queue.fail_task(task.id, f"Budget exceeded: {budget_check.reason}")
            return True

        self.task_queue.start_task(task.id)

        worktree_mgr = self.get_worktree_manager(task.repo, task.github_repo)
        if not worktree_mgr.worktree_exists(task.feature_id):
            worktree_mgr.create_worktree(task.feature_id)

        if task.source == "review":
            first_agent = self.REVIEW_ENTRY_POINT
        else:
            first_agent = self.AGENT_SEQUENCE[0]

        self.start_agent_session(
            agent=first_agent,
            feature_id=task.feature_id,
            task_id=task.id,
            repo=task.repo,
            github_repo=task.github_repo,
        )

        return True

    def start_agent_session(
        self,
        agent: str,
        feature_id: str,
        task_id: int,
        repo: str = "falara",
        github_repo: str = "borisdeluxe/falara",
    ) -> None:
        """Start a new agent session in tmux."""
        session_name = f"{feature_id}-{agent.split('_')[0]}"

        feature_pipeline = self.pipeline_dir / feature_id
        feature_pipeline.mkdir(parents=True, exist_ok=True)

        worktree_mgr = self.get_worktree_manager(repo, github_repo)
        repo_dir = worktree_mgr.get_worktree_path(feature_id)
        if not repo_dir.exists():
            repo_dir = self.repos_dir / repo
        output_file = self.AGENT_OUTPUT_ARTIFACTS.get(agent, "output.md")
        input_file = feature_pipeline / "input.md"
        output_path = feature_pipeline / output_file

        # Read input content for prompt
        input_content = ""
        if input_file.exists():
            input_content = input_file.read_text()

        # Metadata file for cost tracking (Claude CLI JSON output)
        meta_path = feature_pipeline / f"{agent}.meta.json"

        # Claude Code invocation:
        # --agent loads from ~/.claude/agents/<agent>.md
        # -p for non-interactive print mode
        # --output-format json outputs metadata including total_cost_usd
        # --dangerously-skip-permissions for automation
        # Use shlex.quote for shell-safe escaping of user content
        #
        # We capture JSON output to meta_path for cost extraction,
        # then extract the "result" field into the artifact file.
        quoted_content = shlex.quote(input_content)
        claude_cmd = (
            f"cd {repo_dir} && "
            f"claude --agent {agent} -p "
            f"--output-format json "
            f"--dangerously-skip-permissions "
            f"{quoted_content} "
            f"> {meta_path} 2>&1; "
            f"python3 -c \"import json,sys; "
            f"d=json.load(open('{meta_path}')); "
            f"print(d.get('result',''))\" > {output_path}; "
            f"echo 'STATUS: Agent {agent} completed' >> {output_path}"
        )

        cmd = ["tmux", "new-session", "-d", "-s", session_name, claude_cmd]

        subprocess.run(cmd, check=False)

        self._active_sessions[feature_id] = AgentSession(
            feature_id=feature_id,
            task_id=task_id,
            current_agent=agent,
            tmux_session=session_name,
            repo=repo,
            github_repo=github_repo,
        )

        self.task_queue.update_current_agent(task_id, agent)

    def check_session_status(self, session_name: str) -> str:
        """Check if tmux session is still running."""
        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True,
        )
        return "running" if result.returncode == 0 else "completed"

    def check_active_sessions(self) -> None:
        """Check all active sessions and handle completions."""
        completed = []

        for feature_id, session in self._active_sessions.items():
            status = self.check_session_status(session.tmux_session)

            if status == "completed":
                self._handle_session_complete(session)
                completed.append(feature_id)

        for feature_id in completed:
            del self._active_sessions[feature_id]

    def _handle_session_complete(self, session: AgentSession) -> None:
        """Handle a completed agent session."""
        cost = self.get_session_cost(
            session.tmux_session,
            feature_id=session.feature_id,
            agent=session.current_agent,
        )
        self.task_queue.add_cost(session.task_id, cost)

        artifact_path = (
            self.pipeline_dir
            / session.feature_id
            / self.AGENT_OUTPUT_ARTIFACTS.get(session.current_agent, "output.md")
        )

        gate_result = self.gate.validate_artifact_file(artifact_path, session.current_agent)

        if gate_result.status == GateStatus.PASSED:
            if gate_result.next_agent:
                self.start_agent_session(
                    agent=gate_result.next_agent,
                    feature_id=session.feature_id,
                    task_id=session.task_id,
                    repo=session.repo,
                    github_repo=session.github_repo,
                )
            else:
                self._create_pr_and_complete(session, cost)

        elif gate_result.status == GateStatus.RETURN:
            retry_check = self.gate.check_retry_limit(
                session.feature_id,
                gate_result.return_to,
            )

            if retry_check.escalate:
                self.notify_escalation(session, gate_result)
            else:
                self.gate.increment_retry(session.feature_id, gate_result.return_to)
                self.start_agent_session(
                    agent=gate_result.return_to,
                    feature_id=session.feature_id,
                    task_id=session.task_id,
                    repo=session.repo,
                    github_repo=session.github_repo,
                )

        elif gate_result.status == GateStatus.FAILED:
            self.task_queue.fail_task(session.task_id, gate_result.reason)

        elif gate_result.status == GateStatus.BLOCKED:
            self.notify_escalation(session, gate_result)

    def _create_pr_and_complete(self, session: AgentSession, cost: float) -> None:
        """Create PR for completed task and mark as complete."""
        try:
            worktree_mgr = self.get_worktree_manager(session.repo, session.github_repo)
            pr_result = worktree_mgr.create_pr(
                feature_id=session.feature_id,
                title=f"feat: {session.feature_id}",
                body=f"Automated PR from Mutirada pipeline.\n\nFeature ID: {session.feature_id}",
            )
            print(f"PR created: {pr_result.get('html_url', 'unknown')}")
        except Exception as e:
            print(f"Warning: Failed to create PR for {session.feature_id}: {e}")

        self.task_queue.complete_task(session.task_id, cost)

    def get_session_cost(
        self,
        session_name: str,
        feature_id: Optional[str] = None,
        agent: Optional[str] = None,
    ) -> float:
        """Get API cost from completed session by reading Claude CLI JSON output.

        Args:
            session_name: The tmux session name (for backward compat, unused now)
            feature_id: The feature ID to locate the metadata file
            agent: The agent name to locate the metadata file

        Returns:
            The total cost in USD, or 0.0 if metadata is unavailable.
        """
        if not feature_id or not agent:
            # Backward compatibility: no metadata available without feature_id/agent
            return 0.0

        meta_path = self.pipeline_dir / feature_id / f"{agent}.meta.json"

        if not meta_path.exists():
            return 0.0

        try:
            with open(meta_path) as f:
                data = json.load(f)
            return float(data.get("total_cost_usd", 0.0))
        except (json.JSONDecodeError, ValueError, OSError):
            return 0.0

    def notify_escalation(self, session: AgentSession, gate_result) -> None:
        """Send Slack notification for escalation. Placeholder for now."""
        pass

    def _handle_shutdown(self, signum, frame) -> None:
        """Handle shutdown signals (SIGTERM, SIGINT)."""
        sig_name = signal.Signals(signum).name
        print(f"\nReceived {sig_name}, initiating graceful shutdown...")
        self._shutdown_requested = True

    def _graceful_shutdown(self) -> None:
        """Perform graceful shutdown: log sessions and optionally kill them."""
        if not self._active_sessions:
            print("No active sessions. Shutting down cleanly.")
            return

        print(f"Active sessions at shutdown ({len(self._active_sessions)}):")
        for feature_id, session in self._active_sessions.items():
            print(f"  - {feature_id}: agent={session.current_agent}, tmux={session.tmux_session}")

        if self._kill_sessions_on_shutdown:
            print("Killing tmux sessions...")
            for feature_id, session in self._active_sessions.items():
                subprocess.run(
                    ["tmux", "kill-session", "-t", session.tmux_session],
                    capture_output=True,
                )
                print(f"  Killed {session.tmux_session}")

        print("Orchestrator shutdown complete.")

    def run_loop(self, interval: int = 30) -> None:
        """Main loop - process tasks and check sessions."""
        import time

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        print(f"Orchestrator starting, polling every {interval}s...")
        while not self._shutdown_requested:
            try:
                processed = self.process_one()
                if processed:
                    print(f"Processed task")
                self.check_active_sessions()
            except Exception as e:
                print(f"Error in loop: {e}")
            time.sleep(interval)

        self._graceful_shutdown()


def main():
    """Entry point for orchestrator service."""
    import psycopg
    from psycopg.rows import dict_row

    db_url = os.environ.get(
        'DATABASE_URL',
        'postgresql://agency:agency@localhost:5432/agency_db'
    )

    print(f"Connecting to database...")
    db = psycopg.connect(db_url, row_factory=dict_row, autocommit=True)
    print(f"Connected. Starting orchestrator...")

    orch = Orchestrator(
        db=db,
        github_token=os.environ.get("GITHUB_TOKEN"),
    )
    orch.run_loop(interval=30)


if __name__ == '__main__':
    main()
