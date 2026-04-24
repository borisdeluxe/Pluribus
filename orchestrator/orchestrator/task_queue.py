"""Task queue operations - manages persistent tasks in Postgres."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    id: int
    feature_id: str
    source: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cost_eur: float = 0.0
    current_agent: Optional[str] = None
    error: Optional[str] = None


class TaskQueue:
    """Manages task queue in Postgres."""

    def __init__(self, db):
        self.db = db

    def fetch_pending(self) -> Optional[Task]:
        raise NotImplementedError

    def get_task(self, task_id: int) -> Task:
        raise NotImplementedError

    def start_task(self, task_id: int) -> None:
        raise NotImplementedError

    def complete_task(self, task_id: int, cost_eur: float) -> None:
        raise NotImplementedError

    def fail_task(self, task_id: int, error: str) -> None:
        raise NotImplementedError

    def cancel_task(self, task_id: int) -> None:
        raise NotImplementedError

    def update_current_agent(self, task_id: int, agent: str) -> None:
        raise NotImplementedError

    def add_cost(self, task_id: int, amount: float) -> None:
        raise NotImplementedError
