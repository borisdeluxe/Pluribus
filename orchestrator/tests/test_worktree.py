"""Tests for git worktree management."""
import os
import pytest
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from orchestrator.worktree import WorktreeManager, WorktreeError


@pytest.fixture
def git_repo(tmp_path):
    """Create a test git repo with main branch."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_dir, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir, capture_output=True)
    (repo_dir / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_dir, capture_output=True)
    return repo_dir


class TestWorktreeCreation:
    """Worktree creation for feature isolation."""

    def test_create_worktree_creates_branch_and_directory(self, git_repo, tmp_path):
        """Should create a new branch and worktree directory."""
        worktree_dir = tmp_path / "worktrees"
        manager = WorktreeManager(git_repo, worktree_dir)

        wt_path = manager.create_worktree("FAL-123")

        assert wt_path.exists()
        assert (wt_path / "README.md").exists()
        assert wt_path == worktree_dir / "FAL-123"

    def test_create_worktree_branch_name_matches_feature_id(self, git_repo, tmp_path):
        """Branch name should be feature/<feature_id>."""
        worktree_dir = tmp_path / "worktrees"
        manager = WorktreeManager(git_repo, worktree_dir)

        wt_path = manager.create_worktree("FAL-123")

        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=wt_path,
            capture_output=True,
            text=True
        )
        assert result.stdout.strip() == "feature/FAL-123"

    def test_create_worktree_fails_if_already_exists(self, git_repo, tmp_path):
        """Should raise error if worktree already exists."""
        worktree_dir = tmp_path / "worktrees"
        manager = WorktreeManager(git_repo, worktree_dir)

        manager.create_worktree("FAL-123")

        with pytest.raises(WorktreeError, match="already exists"):
            manager.create_worktree("FAL-123")

    def test_get_worktree_path_returns_correct_path(self, tmp_path):
        """Should return the worktree path for a feature."""
        repo_dir = tmp_path / "repo"
        worktree_dir = tmp_path / "worktrees"
        manager = WorktreeManager(repo_dir, worktree_dir)

        path = manager.get_worktree_path("FAL-456")

        assert path == worktree_dir / "FAL-456"


class TestWorktreeDeletion:
    """Worktree cleanup after task completion."""

    def test_delete_worktree_removes_directory_and_branch(self, git_repo, tmp_path):
        """Should remove worktree directory and delete branch."""
        worktree_dir = tmp_path / "worktrees"
        manager = WorktreeManager(git_repo, worktree_dir)

        wt_path = manager.create_worktree("FAL-123")
        assert wt_path.exists()

        manager.delete_worktree("FAL-123")

        assert not wt_path.exists()

    def test_delete_worktree_ignores_nonexistent(self, git_repo, tmp_path):
        """Should not raise error if worktree doesn't exist."""
        worktree_dir = tmp_path / "worktrees"
        manager = WorktreeManager(git_repo, worktree_dir)

        manager.delete_worktree("NONEXISTENT-999")  # Should not raise


class TestWorktreeExists:
    """Check if worktree exists."""

    def test_worktree_exists_returns_true_when_exists(self, git_repo, tmp_path):
        """Should return True if worktree exists."""
        worktree_dir = tmp_path / "worktrees"
        manager = WorktreeManager(git_repo, worktree_dir)

        manager.create_worktree("FAL-123")

        assert manager.worktree_exists("FAL-123") is True

    def test_worktree_exists_returns_false_when_not_exists(self, tmp_path):
        """Should return False if worktree doesn't exist."""
        repo_dir = tmp_path / "repo"
        worktree_dir = tmp_path / "worktrees"
        manager = WorktreeManager(repo_dir, worktree_dir)

        assert manager.worktree_exists("NONEXISTENT") is False


class TestPRCreation:
    """PR creation after successful pipeline completion."""

    def test_create_pr_pushes_branch_and_creates_pr(self, tmp_path):
        """Should push branch and create PR via GitHub API."""
        repo_dir = tmp_path / "repo"
        worktree_dir = tmp_path / "worktrees"
        manager = WorktreeManager(
            repo_dir,
            worktree_dir,
            github_token="test-token",
            github_repo="owner/repo"
        )

        with patch('orchestrator.worktree.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            with patch('orchestrator.worktree.requests.post') as mock_post:
                mock_post.return_value = MagicMock(
                    status_code=201,
                    json=lambda: {"html_url": "https://github.com/owner/repo/pull/1", "number": 1}
                )

                result = manager.create_pr(
                    feature_id="FAL-123",
                    title="Add feature FAL-123",
                    body="Automated PR from Mutirada pipeline"
                )

        assert result["number"] == 1
        assert "html_url" in result

        mock_run.assert_called()
        mock_post.assert_called_once()

    def test_create_pr_includes_feature_id_in_branch(self, tmp_path):
        """PR should be from feature/<feature_id> branch."""
        repo_dir = tmp_path / "repo"
        worktree_dir = tmp_path / "worktrees"
        manager = WorktreeManager(
            repo_dir,
            worktree_dir,
            github_token="test-token",
            github_repo="owner/repo"
        )

        with patch('orchestrator.worktree.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            with patch('orchestrator.worktree.requests.post') as mock_post:
                mock_post.return_value = MagicMock(
                    status_code=201,
                    json=lambda: {"html_url": "https://github.com/owner/repo/pull/1", "number": 1}
                )

                manager.create_pr("FAL-123", "Title", "Body")

        call_args = mock_post.call_args
        json_data = call_args[1]["json"]
        assert json_data["head"] == "feature/FAL-123"
        assert json_data["base"] == "main"


class TestOrchestratorWorktreeIntegration:
    """Orchestrator integration with worktree manager."""

    def test_process_one_creates_worktree_for_new_task(self, tmp_path):
        """Should create worktree when starting a new task."""
        from orchestrator.main import Orchestrator
        from unittest.mock import MagicMock, patch

        mock_db = MagicMock()
        mock_task = MagicMock()
        mock_task.id = 1
        mock_task.feature_id = "FAL-123"
        mock_task.source = "api"

        with patch.object(Orchestrator, '__init__', lambda self, **kwargs: None):
            orch = Orchestrator.__new__(Orchestrator)
            orch.db = mock_db
            orch.task_queue = MagicMock()
            orch.task_queue.fetch_pending.return_value = mock_task
            orch.budget = MagicMock()
            orch.budget.can_spend.return_value = MagicMock(allowed=True)
            orch.gate = MagicMock()
            orch.pipeline_dir = tmp_path / "pipeline"
            orch.worktree_dir = tmp_path / "worktrees"
            orch._active_sessions = {}
            orch.worktree_manager = MagicMock()
            orch.worktree_manager.worktree_exists.return_value = False
            orch.AGENT_SEQUENCE = ["concept_clarifier"]

            with patch.object(orch, 'start_agent_session'):
                orch.process_one()

        orch.worktree_manager.create_worktree.assert_called_once_with("FAL-123")

    def test_handle_session_complete_creates_pr_after_final_agent(self, tmp_path):
        """Should create PR when deploy_runner completes successfully."""
        from orchestrator.main import Orchestrator, AgentSession
        from orchestrator.gate import GateStatus
        from unittest.mock import MagicMock, patch

        mock_db = MagicMock()

        with patch.object(Orchestrator, '__init__', lambda self, **kwargs: None):
            orch = Orchestrator.__new__(Orchestrator)
            orch.db = mock_db
            orch.task_queue = MagicMock()
            orch.budget = MagicMock()
            orch.gate = MagicMock()
            orch.gate.validate_artifact_file.return_value = MagicMock(
                status=GateStatus.PASSED,
                next_agent=None  # No next agent = final
            )
            orch.pipeline_dir = tmp_path / "pipeline"
            orch.worktree_dir = tmp_path / "worktrees"
            orch._active_sessions = {}
            orch.worktree_manager = MagicMock()
            orch.worktree_manager.create_pr.return_value = {"number": 1, "html_url": "..."}
            orch.AGENT_OUTPUT_ARTIFACTS = {"deploy_runner": "deploy-log.md"}

            session = AgentSession(
                feature_id="FAL-123",
                task_id=1,
                current_agent="deploy_runner",
                tmux_session="FAL-123-deploy"
            )

            (tmp_path / "pipeline" / "FAL-123").mkdir(parents=True)
            (tmp_path / "pipeline" / "FAL-123" / "deploy-log.md").write_text("STATUS: ready")

            with patch.object(orch, 'get_session_cost', return_value=0.10):
                orch._handle_session_complete(session)

        orch.worktree_manager.create_pr.assert_called_once()
        orch.task_queue.complete_task.assert_called_once()
