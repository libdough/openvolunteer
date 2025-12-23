#!/usr/bin/env python3
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ActivityType:
    key: str  # e.g. "call", "knock", "phonebank_attempt"
    label: str  # "Call"
    kind: str  # maps to Activity.kind, or you can set to "custom"
    validate: Callable[[dict], None] = lambda data: None


_REGISTRY: dict[str, ActivityType] = {}


def register_activity_type(activity_type: ActivityType) -> None:
    if activity_type.key in _REGISTRY:
        msg = f"Activity type already registered: {activity_type.key}"
        raise ValueError(msg)
    _REGISTRY[activity_type.key] = activity_type


def get_activity_types() -> list[ActivityType]:
    return list(_REGISTRY.values())


def get_activity_type(key: str) -> ActivityType:
    return _REGISTRY[key]
