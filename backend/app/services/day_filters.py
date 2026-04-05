from datetime import datetime

VALID_WEEKDAYS = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)


def normalize_day_override(day_override: str | None) -> str | None:
    if day_override is None:
        return None
    normalized = day_override.strip().title()
    if not normalized:
        return None
    if normalized not in VALID_WEEKDAYS:
        raise ValueError("day_override must be one of Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday")
    return normalized


def resolve_applied_day(day_override: str | None) -> str:
    normalized = normalize_day_override(day_override)
    if normalized:
        return normalized
    return datetime.now().strftime("%A")
