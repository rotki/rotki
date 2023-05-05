from typing import Literal, NamedTuple


class TimestampOrBlockRange(NamedTuple):
    range_type: Literal['timestamps', 'blocks']
    from_value: int
    to_value: int
