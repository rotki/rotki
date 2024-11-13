from enum import Enum, auto


class BalancerV1EventTypes(Enum):
    JOIN = auto()
    EXIT = auto()
