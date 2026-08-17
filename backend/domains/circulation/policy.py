"""Circulation policy read from settings.

Nothing in ``services.py`` hard-codes a number; every rule from §3 of the plan is looked up
here so it stays tunable per deployment.
"""

from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings


@dataclass(frozen=True)
class CirculationPolicy:
    max_active_loans: int
    loan_period_days: int
    max_renewals: int
    overdue_fine_per_day: Decimal
    default_replacement_cost: Decimal
    hold_shelf_days: int
    unpaid_fine_block_threshold: Decimal


def get_policy() -> CirculationPolicy:
    raw = settings.CIRCULATION
    return CirculationPolicy(
        max_active_loans=int(raw["MAX_ACTIVE_LOANS"]),
        loan_period_days=int(raw["LOAN_PERIOD_DAYS"]),
        max_renewals=int(raw["MAX_RENEWALS"]),
        overdue_fine_per_day=Decimal(raw["OVERDUE_FINE_PER_DAY"]),
        default_replacement_cost=Decimal(raw["DEFAULT_REPLACEMENT_COST"]),
        hold_shelf_days=int(raw["HOLD_SHELF_DAYS"]),
        unpaid_fine_block_threshold=Decimal(raw["UNPAID_FINE_BLOCK_THRESHOLD"]),
    )
