from typing import Any, Callable, Dict, NamedTuple, Optional


class UpgradeRecord(NamedTuple):
    from_version: int
    function: Callable
    kwargs: Optional[Dict[str, Any]] = None
