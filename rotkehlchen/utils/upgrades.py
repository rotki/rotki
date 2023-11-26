from collections.abc import Callable
from typing import Any, NamedTuple


class UpgradeRecord(NamedTuple):
    from_version: int
    function: Callable
    kwargs: dict[str, Any] | None = None
