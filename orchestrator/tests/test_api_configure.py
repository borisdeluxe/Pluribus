"""Tests for /api/configure endpoints."""
import pytest
from fastapi.testclient import TestClient
import orchestrator.api as api_module
from orchestrator.api import app

client = TestClient(app)
API_SECRET = "dev-secret-change-me"


@pytest.fixture(autouse=True)
def reset_configure_manager():
    """Reset shared ConversationManager state before each test."""
    api_module.configure_manager._sessions.clear()
    yield
    api_module.configure_manager._sessions.clear()


def test_configure_requires_auth():
    response = client.post("/api/configure", json={"repo_url": "https://github.com/test/repo"})
    assert response.status_code == 401


def test_configure_starts_session():
    response = client.post(
        "/api/configure",
        json={"repo_url": "https://github.com/test/repo"},
        headers={"X-Agency-Secret": API_SECRET}
    )
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["state"] in ["DETECTING", "ERROR"]


def test_configure_rejects_invalid_url():
    response = client.post(
        "/api/configure",
        json={"repo_url": "https://evil.com/repo"},
        headers={"X-Agency-Secret": API_SECRET}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "ERROR"


def test_configure_answer_requires_auth():
    response = client.post(
        "/api/configure/abc123/answer",
        json={"answer": "pytest"}
    )
    assert response.status_code == 401


def test_configure_answer_nonexistent_session():
    response = client.post(
        "/api/configure/nonexistent/answer",
        json={"answer": "pytest"},
        headers={"X-Agency-Secret": API_SECRET}
    )
    assert response.status_code == 404


def test_configure_cancel_requires_auth():
    response = client.post("/api/configure/abc123/cancel")
    assert response.status_code == 401


def test_configure_cancel_nonexistent_session():
    response = client.post(
        "/api/configure/nonexistent/cancel",
        headers={"X-Agency-Secret": API_SECRET}
    )
    assert response.status_code == 404


def test_repos_requires_auth():
    response = client.get("/api/repos")
    assert response.status_code == 401


def test_repos_returns_list():
    response = client.get(
        "/api/repos",
        headers={"X-Agency-Secret": API_SECRET}
    )
    assert response.status_code == 200
    data = response.json()
    assert "repos" in data
    assert isinstance(data["repos"], list)
