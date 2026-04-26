"""Tests for gate validation."""
import pytest
from pathlib import Path

from orchestrator.gate import GateValidator, GateResult, GateStatus


class TestGateValidator:
    """Gate validator should check artifact status lines and enforce handoff rules."""

    def test_validate_status_line_passes_ready(self, gate: GateValidator):
        """Should pass when status line indicates ready for next agent."""
        artifact = "# Report\n\nSome content.\n\nSTATUS: READY_FOR_IMPLEMENTER"

        result = gate.validate_artifact(artifact, current_agent="test_designer")

        assert result.status == GateStatus.PASSED
        assert result.next_agent == "implementer"

    def test_validate_status_line_fails_missing(self, gate: GateValidator):
        """Should fail when status line is missing."""
        artifact = "# Report\n\nSome content without status line."

        result = gate.validate_artifact(artifact, current_agent="test_designer")

        assert result.status == GateStatus.FAILED
        assert "missing" in result.reason.lower()

    def test_validate_status_line_fails_invalid_format(self, gate: GateValidator):
        """Should fail when status line has invalid format."""
        artifact = "# Report\n\nSTATUS: SOMETHING_WRONG"

        result = gate.validate_artifact(artifact, current_agent="test_designer")

        assert result.status == GateStatus.FAILED
        assert "invalid" in result.reason.lower()

    def test_validate_return_to_author(self, gate: GateValidator):
        """Should recognize RETURN_TO status as gate failure with retry."""
        artifact = "# Report\n\nSTATUS: RETURN_TO_ARCHITECT_PLANNER"

        result = gate.validate_artifact(artifact, current_agent="security_reviewer")

        assert result.status == GateStatus.RETURN
        assert result.return_to == "architect_planner"

    def test_validate_blocked_status(self, gate: GateValidator):
        """Should recognize BLOCKED status as requiring intervention."""
        artifact = "# Report\n\nSTATUS: BLOCKED_REVIEW_FAILED"

        result = gate.validate_artifact(artifact, current_agent="qa_validator")

        assert result.status == GateStatus.BLOCKED
        assert "review_failed" in result.reason.lower()

    def test_validate_checks_required_sections(self, gate: GateValidator):
        """Should verify required sections are present based on agent role."""
        # QA report missing "Gate Decision" section
        artifact = """# QA Report

## Summary
All good.

STATUS: READY_FOR_DEPLOY_RUNNER
"""
        result = gate.validate_artifact(
            artifact,
            current_agent="qa_validator",
            required_sections=["Summary", "Gate Decision"]
        )

        assert result.status == GateStatus.FAILED
        assert "gate decision" in result.reason.lower()

    def test_validate_file_reads_from_path(self, gate: GateValidator, tmp_path: Path):
        """Should read artifact from file path."""
        artifact_path = tmp_path / "test-report.md"
        artifact_path.write_text("# Report\n\nSTATUS: READY_FOR_IMPLEMENTER")

        result = gate.validate_artifact_file(artifact_path, current_agent="test_designer")

        assert result.status == GateStatus.PASSED

    def test_validate_file_fails_on_missing_file(self, gate: GateValidator, tmp_path: Path):
        """Should fail gracefully when artifact file doesn't exist."""
        missing_path = tmp_path / "nonexistent.md"

        result = gate.validate_artifact_file(missing_path, current_agent="test_designer")

        assert result.status == GateStatus.FAILED
        assert "not found" in result.reason.lower()


class TestGateAgentSequence:
    """Gate should enforce correct agent sequence."""

    def test_valid_sequence_test_designer_to_implementer(self, gate: GateValidator):
        """test_designer -> implementer is valid."""
        assert gate.is_valid_transition("test_designer", "implementer") is True

    def test_valid_sequence_implementer_to_security(self, gate: GateValidator):
        """implementer -> security_reviewer is valid."""
        assert gate.is_valid_transition("implementer", "security_reviewer") is True

    def test_invalid_sequence_skipping_agent(self, gate: GateValidator):
        """test_designer -> qa_validator is invalid (skips implementer)."""
        assert gate.is_valid_transition("test_designer", "qa_validator") is False

    def test_return_sequence_is_valid(self, gate: GateValidator):
        """Returning to earlier agent is always valid."""
        assert gate.is_valid_transition("security_reviewer", "architect_planner") is True


class TestRetryTracking:
    """Gate should track retries per agent."""

    def test_increment_retry_count(self, test_db):
        """Should track retry count per feature/agent pair."""
        test_db.execute(
            "INSERT INTO agency_tasks (feature_id, source, status) VALUES (%s, %s, %s)",
            ("FAL-001", "test", "in_progress")
        )
        test_db.commit()

        gate = GateValidator(test_db)
        gate.increment_retry("FAL-001", "implementer")
        gate.increment_retry("FAL-001", "implementer")

        assert gate.get_retry_count("FAL-001", "implementer") == 2

    def test_max_retries_triggers_escalation(self, test_db):
        """Should indicate escalation needed after max retries."""
        test_db.execute(
            "INSERT INTO agency_tasks (feature_id, source, status) VALUES (%s, %s, %s)",
            ("FAL-001", "test", "in_progress")
        )
        test_db.commit()

        gate = GateValidator(test_db)
        gate.increment_retry("FAL-001", "implementer")
        gate.increment_retry("FAL-001", "implementer")

        result = gate.check_retry_limit("FAL-001", "implementer", max_retries=2)

        assert result.escalate is True


class TestRetryPersistence:
    """Gate should persist retry counts to database, not just in-memory."""

    def test_increment_retry_writes_to_database(self, test_db):
        """Should write retry count to database on increment."""
        # Add a task first
        test_db.execute(
            "INSERT INTO agency_tasks (feature_id, source, status) VALUES (%s, %s, %s)",
            ("FAL-101", "test", "in_progress")
        )
        test_db.commit()

        gate = GateValidator(test_db)
        gate.increment_retry("FAL-101", "implementer")

        # Verify it was written to DB by checking the data column
        result = test_db.execute(
            "SELECT data FROM agency_tasks WHERE feature_id = %s",
            ("FAL-101",)
        ).fetchone()

        assert result is not None
        assert result["data"] is not None
        retry_counts = result["data"].get("retry_counts", {})
        assert retry_counts.get("implementer") == 1

    def test_get_retry_count_reads_from_database(self, test_db):
        """Should read retry count from database, not in-memory cache."""
        # Add a task with existing retry counts in data
        test_db.execute(
            """INSERT INTO agency_tasks (feature_id, source, status, data)
               VALUES (%s, %s, %s, %s)""",
            ("FAL-102", "test", "in_progress", '{"retry_counts": {"implementer": 3}}')
        )
        test_db.commit()

        gate = GateValidator(test_db)
        count = gate.get_retry_count("FAL-102", "implementer")

        assert count == 3

    def test_retry_counts_survive_new_gate_instance(self, test_db):
        """Retry counts should persist across GateValidator instances."""
        # Add a task
        test_db.execute(
            "INSERT INTO agency_tasks (feature_id, source, status) VALUES (%s, %s, %s)",
            ("FAL-103", "test", "in_progress")
        )
        test_db.commit()

        # First gate instance increments
        gate1 = GateValidator(test_db)
        gate1.increment_retry("FAL-103", "security_reviewer")
        gate1.increment_retry("FAL-103", "security_reviewer")

        # Second gate instance (simulating restart) should see the count
        gate2 = GateValidator(test_db)
        count = gate2.get_retry_count("FAL-103", "security_reviewer")

        assert count == 2

    def test_retry_counts_per_agent_isolated(self, test_db):
        """Retry counts should be tracked separately per agent."""
        test_db.execute(
            "INSERT INTO agency_tasks (feature_id, source, status) VALUES (%s, %s, %s)",
            ("FAL-104", "test", "in_progress")
        )
        test_db.commit()

        gate = GateValidator(test_db)
        gate.increment_retry("FAL-104", "implementer")
        gate.increment_retry("FAL-104", "implementer")
        gate.increment_retry("FAL-104", "security_reviewer")

        assert gate.get_retry_count("FAL-104", "implementer") == 2
        assert gate.get_retry_count("FAL-104", "security_reviewer") == 1
        assert gate.get_retry_count("FAL-104", "refactorer") == 0

    def test_check_retry_limit_uses_persisted_count(self, test_db):
        """check_retry_limit should use persisted count from database."""
        # Add task with retry count at the limit
        test_db.execute(
            """INSERT INTO agency_tasks (feature_id, source, status, data)
               VALUES (%s, %s, %s, %s)""",
            ("FAL-105", "test", "in_progress", '{"retry_counts": {"implementer": 2}}')
        )
        test_db.commit()

        gate = GateValidator(test_db)
        result = gate.check_retry_limit("FAL-105", "implementer", max_retries=2)

        assert result.escalate is True
        assert result.retry_count == 2


@pytest.fixture
def gate(mock_db):
    """Gate validator instance."""
    return GateValidator(mock_db)
