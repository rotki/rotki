from typing import Any, Callable, NamedTuple, Optional


class UpgradeRecord(NamedTuple):
    from_version: int
    function: Callable
    kwargs: Optional[dict[str, Any]] = None
