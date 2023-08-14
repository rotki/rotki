from enum import auto
from typing import Literal, NamedTuple, Optional

from rotkehlchen.utils.mixins.enums import SerializableEnumNameMixin


class CounterpartyDetails(NamedTuple):
    identifier: str
    label: str
    image: str


class EventCategoryDetails(NamedTuple):
    label: str
    icon: str
    color: Optional[Literal['green', 'red']] = None


class EventCategory(SerializableEnumNameMixin):
    """
    User friendly categories to classify combinations of event type and event subtype
    """
    GAS = auto()
    SEND = auto()
    RECEIVE = auto()
    SWAP_OUT = auto()
    SWAP_IN = auto()
    APPROVAL = auto()
    DEPOSIT = auto()
    WITHDRAW = auto()
    AIRDROP = auto()
    BORROW = auto()
    REPAY = auto()
    DEPLOY = auto()
    BRIDGE_IN = auto()
    BRIDGE_OUT = auto()
    GOVERNANCE = auto()
    DONATE = auto()
    RECEIVE_DONATION = auto()
    RENEW = auto()
    PLACE_ORDER = auto()
    TRANSFER = auto()
    CLAIM_REWARD = auto()
    LIQUIDATE = auto()
    INFORMATIONAL = auto()
    CANCEL_ORDER = auto()
    REFUND = auto()
    FEE = auto()
    MEV_REWARD = auto()
    CREATE_BLOCK = auto()
