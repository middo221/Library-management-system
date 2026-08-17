"""Structured logging for state-changing service calls.

Every mutation records who did what to which object, so the log is answerable after the
fact without an audit table (which §8 puts out of scope).
"""

import logging
from typing import Any

logger = logging.getLogger("library.audit")


def log_action(action: str, *, actor: Any = None, **fields: Any) -> None:
    parts = [f"action={action}"]
    if actor is not None:
        parts.append(f"actor={getattr(actor, 'email', actor)}")
        parts.append(f"actor_id={getattr(actor, 'id', None)}")
    parts.extend(f"{key}={value}" for key, value in fields.items())
    logger.info(" ".join(parts))
