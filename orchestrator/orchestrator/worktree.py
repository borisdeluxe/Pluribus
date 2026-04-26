"""Git worktree management for feature isolation."""
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

import requests


class WorktreeError(Exception):
    """Error during worktree operations."""
    pass


class WorktreeManager:
    """Manages git worktrees for feature branches."""

    def __init__(
        self,
        repo_dir: Path,
        worktree_dir: Path,
        github_token: Optional[str] = None,
        github_repo: Optional[str] = None,
        base_branch: str = "main",
    ):
        self.repo_dir = Path(repo_dir)
        self.worktree_dir = Path(worktree_dir)
        self.github_token = github_token
        self.github_repo = github_repo
        self.base_branch = base_branch

        self.worktree_dir.mkdir(parents=True, exist_ok=True)

    def get_worktree_path(self, feature_id: str) -> Path:
        """Get the worktree path for a feature."""
        return self.worktree_dir / feature_id

    def get_branch_name(self, feature_id: str) -> str:
        """Get the branch name for a feature."""
        return f"feature/{feature_id}"

    def worktree_exists(self, feature_id: str) -> bool:
        """Check if worktree exists for a feature."""
        wt_path = self.get_worktree_path(feature_id)
        return wt_path.exists()

    def create_worktree(self, feature_id: str) -> Path:
        """Create a new worktree for a feature.

        Creates a new branch feature/<feature_id> from base_branch
        and sets up a worktree at worktree_dir/<feature_id>.
        """
        wt_path = self.get_worktree_path(feature_id)
        branch_name = self.get_branch_name(feature_id)

        if wt_path.exists():
            raise WorktreeError(f"Worktree already exists: {wt_path}")

        result = subprocess.run(
            ["git", "worktree", "add", "-b", branch_name, str(wt_path), self.base_branch],
            cwd=self.repo_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise WorktreeError(f"Failed to create worktree: {result.stderr}")

        return wt_path

    def delete_worktree(self, feature_id: str, delete_branch: bool = True) -> None:
        """Delete worktree and optionally the branch.

        Safe to call even if worktree doesn't exist.
        """
        wt_path = self.get_worktree_path(feature_id)
        branch_name = self.get_branch_name(feature_id)

        if not wt_path.exists():
            return

        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt_path)],
            cwd=self.repo_dir,
            capture_output=True,
        )

        if delete_branch:
            subprocess.run(
                ["git", "branch", "-D", branch_name],
                cwd=self.repo_dir,
                capture_output=True,
            )

    def push_branch(self, feature_id: str, remote: str = "origin") -> None:
        """Push the feature branch to remote."""
        branch_name = self.get_branch_name(feature_id)
        wt_path = self.get_worktree_path(feature_id)

        result = subprocess.run(
            ["git", "push", "-u", remote, branch_name],
            cwd=wt_path,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise WorktreeError(f"Failed to push branch: {result.stderr}")

    def create_pr(
        self,
        feature_id: str,
        title: str,
        body: str,
    ) -> Dict[str, Any]:
        """Create a pull request for the feature branch.

        Pushes branch and creates PR via GitHub API.
        Returns PR data including 'number' and 'html_url'.
        """
        if not self.github_token or not self.github_repo:
            raise WorktreeError("GitHub token and repo required for PR creation")

        branch_name = self.get_branch_name(feature_id)

        self.push_branch(feature_id)

        response = requests.post(
            f"https://api.github.com/repos/{self.github_repo}/pulls",
            headers={
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json",
            },
            json={
                "title": title,
                "head": branch_name,
                "base": self.base_branch,
                "body": body,
            },
        )

        if response.status_code != 201:
            raise WorktreeError(f"Failed to create PR: {response.text}")

        return response.json()

    def delete_remote_branch(self, feature_id: str, remote: str = "origin") -> None:
        """Delete the feature branch from remote."""
        branch_name = self.get_branch_name(feature_id)

        subprocess.run(
            ["git", "push", remote, "--delete", branch_name],
            cwd=self.repo_dir,
            capture_output=True,
        )
