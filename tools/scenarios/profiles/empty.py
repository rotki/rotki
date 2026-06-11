"""The empty profile: a fresh user with default settings and no data.

Baseline for boot/login/first-run measurements.
"""
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tools.scenarios.base import ProfileBuilder


def build(builder: 'ProfileBuilder') -> dict[str, Any] | None:
    return None  # user creation alone is the whole profile
