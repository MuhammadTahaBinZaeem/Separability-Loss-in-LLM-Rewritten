"""Validate reported completion without inventing exact timestamps or issue dates."""
from datetime import datetime, timezone


def completion_window(record, issued_utc, *, current_utc=None):
    issued = datetime.fromisoformat(issued_utc)
    current = current_utc or datetime.now(timezone.utc)
    if issued.tzinfo is None or current.tzinfo is None:
        raise ValueError("Review chronology requires timezone-aware boundaries")
    exact = record.get("completed_utc")
    window = record.get("completion_window")
    if bool(exact) == bool(window):
        raise ValueError("Supply exactly one completion timestamp or reported completion window")
    if exact:
        lower = upper = datetime.fromisoformat(exact)
    else:
        if (not isinstance(window, dict) or window.get("precision") != "bounded_interval"
            or not isinstance(window.get("basis"), str) or not window["basis"].strip()):
            raise ValueError("A reported completion window requires its basis and precision")
        lower = datetime.fromisoformat(window["earliest_utc"])
        upper = datetime.fromisoformat(window["latest_utc"])
    if lower.tzinfo is None or upper.tzinfo is None or not issued <= lower <= upper <= current:
        raise ValueError("Review completion must be timezone-aware, after issuance and not in the future")
    return lower, upper
