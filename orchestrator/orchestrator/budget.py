"""Budget enforcement - prevents overspend at feature, daily, and weekly levels."""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


class BudgetExceeded(Exception):
    """Raised when a budget limit would be exceeded."""
    pass


@dataclass
class BudgetLimits:
    per_feature_eur: float = 5.00
    per_day_eur: float = 20.00
    per_week_eur: float = 100.00


@dataclass
class BudgetCheckResult:
    allowed: bool
    current: float = 0.0
    limit: float = 0.0
    remaining: float = 0.0
    exceeded_by: float = 0.0
    reason: str = ""


@dataclass
class CanSpendResult:
    allowed: bool
    feature_remaining: float = 0.0
    daily_remaining: float = 0.0
    weekly_remaining: float = 0.0
    reason: str = ""


class BudgetEnforcer:
    """Enforces budget limits at feature, daily, and weekly levels."""

    def __init__(self, db, limits: Optional[BudgetLimits] = None):
        self.db = db
        self.limits = limits or BudgetLimits()

    def check_feature_budget(self, feature_id: str, current_cost: float) -> BudgetCheckResult:
        raise NotImplementedError

    def check_daily_budget(self) -> BudgetCheckResult:
        raise NotImplementedError

    def check_weekly_budget(self) -> BudgetCheckResult:
        raise NotImplementedError

    def can_spend(self, feature_id: str, amount: float) -> CanSpendResult:
        raise NotImplementedError

    def record_spend(self, feature_id: str, amount: float) -> None:
        raise NotImplementedError

    def get_summary(self) -> dict:
        raise NotImplementedError
