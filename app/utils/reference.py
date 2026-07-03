"""Human-readable document reference generation (e.g. ``IN-20260703-000123``)."""
from __future__ import annotations

from datetime import datetime, timezone


def generate_reference(prefix: str, sequence: int) -> str:
    """Build a document reference from a prefix, current date and a sequence.

    Args:
        prefix: Short document type prefix, e.g. ``"IN"`` or ``"OUT"``.
        sequence: A monotonically increasing integer (e.g. row count + 1).

    Returns:
        A reference string such as ``IN-20260703-000123``.
    """
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{prefix}-{today}-{sequence:06d}"
