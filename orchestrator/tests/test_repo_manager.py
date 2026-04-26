import pytest
from orchestrator.agent_designer.repo_manager import RepoManager

def test_validate_url_accepts_github():
    rm = RepoManager()
    assert rm.validate_url("https://github.com/user/repo") is True
    assert rm.validate_url("https://github.com/user/repo.git") is True

def test_validate_url_accepts_gitlab():
    rm = RepoManager()
    assert rm.validate_url("https://gitlab.com/user/repo") is True

def test_validate_url_rejects_unknown_hosts():
    rm = RepoManager()
    assert rm.validate_url("https://evil.com/repo") is False
    assert rm.validate_url("https://github.evil.com/repo") is False

def test_validate_url_rejects_non_https():
    rm = RepoManager()
    assert rm.validate_url("file:///etc/passwd") is False
    assert rm.validate_url("git://github.com/user/repo") is False

def test_validate_url_rejects_path_traversal():
    rm = RepoManager()
    assert rm.validate_url("https://github.com/user/../etc") is False

def test_extract_name_simple():
    rm = RepoManager()
    assert rm.extract_name("https://github.com/user/my-repo") == "my-repo"
    assert rm.extract_name("https://github.com/user/repo.git") == "repo"

def test_extract_name_with_trailing_slash():
    rm = RepoManager()
    assert rm.extract_name("https://github.com/user/repo/") == "repo"

def test_extract_name_rejects_traversal():
    rm = RepoManager()
    with pytest.raises(ValueError):
        rm.extract_name("https://github.com/user/..%2fetc")

def test_extract_name_rejects_empty():
    rm = RepoManager()
    with pytest.raises(ValueError):
        rm.extract_name("https://github.com/")
