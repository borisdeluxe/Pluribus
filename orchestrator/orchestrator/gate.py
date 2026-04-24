"""Gate validation - checks artifact status lines and enforces handoff rules."""
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, List


class GateStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    RETURN = "return"
    BLOCKED = "blocked"


@dataclass
class GateResult:
    status: GateStatus
    next_agent: Optional[str] = None
    return_to: Optional[str] = None
    reason: str = ""


@dataclass
class RetryCheckResult:
    escalate: bool
    retry_count: int = 0


class GateValidator:
    """Validates artifact status lines and enforces gate rules."""

    # Valid agent sequence
    AGENT_SEQUENCE = [
        "concept_clarifier",
        "architect_planner",
        "test_designer",
        "implementer",
        "security_reviewer",
        "qa_validator",
        "deploy_runner",
    ]

    def __init__(self, db):
        self.db = db
        self._retry_counts: dict[tuple[str, str], int] = {}

    def validate_artifact(
        self,
        artifact: str,
        current_agent: str,
        required_sections: Optional[List[str]] = None
    ) -> GateResult:
        raise NotImplementedError

    def validate_artifact_file(self, path: Path, current_agent: str) -> GateResult:
        raise NotImplementedError

    def is_valid_transition(self, from_agent: str, to_agent: str) -> bool:
        raise NotImplementedError

    def increment_retry(self, feature_id: str, agent: str) -> None:
        raise NotImplementedError

    def get_retry_count(self, feature_id: str, agent: str) -> int:
        raise NotImplementedError

    def check_retry_limit(
        self, feature_id: str, agent: str, max_retries: int = 2
    ) -> RetryCheckResult:
        raise NotImplementedError
