"""Repository cloning and registration."""

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

ALLOWED_HOSTS = ["github.com", "gitlab.com", "bitbucket.org"]
REPO_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$')


@dataclass
class CloneResult:
    success: bool
    path: Optional[Path] = None
    error: Optional[str] = None


class RepoManager:
    """Manages repository cloning and registration."""

    def __init__(self, repos_dir: Path = None):
        self.repos_dir = repos_dir or Path("/opt/agency/repos")

    def validate_url(self, repo_url: str) -> bool:
        """Validate URL against whitelist. Prevents command injection."""
        try:
            parsed = urlparse(repo_url)
        except Exception:
            return False

        if parsed.scheme not in ("https", "http"):
            return False

        if parsed.hostname not in ALLOWED_HOSTS:
            return False

        if not parsed.path or ".." in parsed.path:
            return False

        return True

    def extract_name(self, repo_url: str) -> str:
        """Extract safe repo name. Prevents path traversal."""
        parsed = urlparse(repo_url)
        path = parsed.path.rstrip("/")
        name = path.split("/")[-1]
        name = name.removesuffix(".git")

        if not name or not REPO_NAME_PATTERN.match(name):
            raise ValueError(f"Invalid repo name: {name}")

        return name

    def clone(self, repo_url: str) -> CloneResult:
        """Clone repo to repos_dir. Returns CloneResult."""
        if not self.validate_url(repo_url):
            return CloneResult(
                success=False,
                error="Invalid URL. Allowed: github.com, gitlab.com, bitbucket.org"
            )

        try:
            name = self.extract_name(repo_url)
        except ValueError as e:
            return CloneResult(success=False, error=str(e))

        target = self.repos_dir / name

        try:
            if target.exists():
                result = subprocess.run(
                    ["git", "-C", str(target), "pull"],
                    capture_output=True, text=True, timeout=300
                )
            else:
                self.repos_dir.mkdir(parents=True, exist_ok=True)
                result = subprocess.run(
                    ["git", "clone", repo_url, str(target)],
                    capture_output=True, text=True, timeout=300
                )

            if result.returncode != 0:
                error_msg = result.stderr.strip()[:200] if result.stderr else "Unknown git error"
                return CloneResult(success=False, error=f"Git error: {error_msg}")

            return CloneResult(success=True, path=target)

        except subprocess.TimeoutExpired:
            return CloneResult(success=False, error="Clone timeout (5 min). Repo too large?")
        except Exception as e:
            return CloneResult(success=False, error=f"Clone error: {str(e)[:200]}")

    def check_existing_agents(self, repo_path: Path) -> bool:
        """Check if .claude/agents/ already exists with content."""
        agents_dir = repo_path / ".claude" / "agents"
        return agents_dir.exists() and any(agents_dir.iterdir())

    def write_agents(self, repo_path: Path, agents: list) -> None:
        """Write generated agents to .claude/agents/"""
        agents_dir = repo_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        for agent in agents:
            filepath = agents_dir / agent["filename"]
            filepath.write_text(agent["content"])

    def cleanup_partial(self, repo_path: Path) -> None:
        """Cleanup partial clone on error."""
        if repo_path and repo_path.exists():
            shutil.rmtree(repo_path, ignore_errors=True)
