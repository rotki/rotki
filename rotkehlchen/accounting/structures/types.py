from enum import Enum, auto
from typing import Literal, NamedTuple, Optional

from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.utils.mixins.enums import DBCharEnumMixIn, SerializableEnumNameMixin

EVM_EVENT_FIELDS = tuple[
    bytes,          # tx_hash
    Optional[str],  # counterparty
    Optional[str],  # product
    Optional[str],  # address
    Optional[str],  # extra_data
]


EVM_EVENT_DB_TUPLE_READ = tuple[
    int,            # identifier
    str,            # event_identifier
    int,            # sequence_index
    int,            # timestamp
    str,            # location
    Optional[str],  # location label
    str,            # asset
    str,            # amount
    str,            # usd value
    Optional[str],  # notes
    str,            # type
    str,            # subtype
    bytes,          # tx_hash
    str,            # address
    Optional[str],  # counterparty
    Optional[str],  # product
    Optional[str],  # extra_data
]


class ActionType(DBCharEnumMixIn):
    TRADE = 1
    ASSET_MOVEMENT = 2
    HISTORY_EVENT = 3
    # ledger action that was removed was 4

    def serialize(self) -> str:
        return self.name.lower()

    @classmethod
    def deserialize(cls, value: str) -> 'ActionType':
        try:
            return getattr(cls, value.upper())
        except AttributeError as e:
            raise DeserializationError(f'Failed to deserialize {cls.__name__} value {value}') from e  # noqa: E501


class HistoryEventType(SerializableEnumNameMixin):
    TRADE = 0
    STAKING = auto()
    DEPOSIT = auto()
    WITHDRAWAL = auto()
    TRANSFER = auto()
    SPEND = auto()
    RECEIVE = auto()
    # forced adjustments of a system, like a CEX. For example having DAO in Kraken
    # and Kraken delisting them and exchanging them for ETH for you
    ADJUSTMENT = auto()
    # An informational event. For kraken entries it means an unknown event
    INFORMATIONAL = auto()
    MIGRATE = auto()
    RENEW = auto()
    DEPLOY = auto()


class HistoryEventSubType(SerializableEnumNameMixin):
    REWARD = 0
    DEPOSIT_ASSET = auto()  # deposit asset in a contract, for staking etc.
    REMOVE_ASSET = auto()  # remove asset from a contract. from staking etc.
    FEE = auto()
    SPEND = auto()
    RECEIVE = auto()
    APPROVE = auto()
    AIRDROP = auto()
    BRIDGE = auto()
    GOVERNANCE = auto()
    NONE = auto()  # Have a value for None to not get into NULL/None comparison hell
    GENERATE_DEBT = auto()
    PAYBACK_DEBT = auto()
    # receive a wrapped asset of something in any protocol. eg cDAI from DAI
    RECEIVE_WRAPPED = auto()
    # return a wrapped asset of something in any protocol. eg. CDAI to DAI
    RETURN_WRAPPED = auto()
    DONATE = auto()
    # subtype for ENS and other NFTs
    NFT = auto()
    # for DXDAO Mesa, Gnosis cowswap etc.
    PLACE_ORDER = auto()
    LIQUIDATE = auto()
    INTEREST_PAYMENT = auto()
    CANCEL_ORDER = auto()  # for cancelling orders like ETH orders in cowswap
    REFUND = auto()  # for refunding, e.g. refunding ETH in cowswap
    BLOCK_PRODUCTION = auto()
    MEV_REWARD = auto()
    APPLY = auto()
    UPDATE = auto()
    CREATE = auto()  # used when tx creates a new entity like Maker vault or Gnosis safe

    def serialize_or_none(self) -> Optional[str]:
        return self.serialize()


class EventDirection(SerializableEnumNameMixin):
    """Describes the direction of an asset's movement (to the user, from the user or neutral)"""
    IN = auto()
    OUT = auto()
    NEUTRAL = auto()


class EventCategoryDetails(NamedTuple):
    label: str
    icon: str
    color: Optional[Literal['green', 'red']] = None


class EventCategory(Enum):
    """User friendly categories to classify combinations of event type and event subtype

    Can't use auto() yet cause has to be only thing in line.
    https://docs.python.org/3/library/enum.html#enum.auto

    From 3.11 and on we will be able to adjust.
    """
    SEND = 1, EventDirection.OUT
    RECEIVE = 2, EventDirection.IN
    SWAP_OUT = 3, EventDirection.OUT
    SWAP_IN = 4, EventDirection.IN
    MIGRATE_OUT = 5, EventDirection.OUT
    MIGRATE_IN = 6, EventDirection.IN
    APPROVAL = 7, EventDirection.NEUTRAL
    DEPOSIT = 8, EventDirection.OUT
    WITHDRAW = 9, EventDirection.IN
    AIRDROP = 10, EventDirection.IN
    BORROW = 11, EventDirection.IN
    REPAY = 12, EventDirection.OUT
    DEPLOY = 12, EventDirection.NEUTRAL
    DEPLOY_WITH_SPEND = 13, EventDirection.OUT
    BRIDGE_DEPOSIT = 14, EventDirection.OUT
    BRIDGE_WITHDRAWAL = 15, EventDirection.IN
    GOVERNANCE = 16, EventDirection.NEUTRAL
    DONATE = 17, EventDirection.OUT
    RECEIVE_DONATION = 18, EventDirection.IN
    RENEW = 19, EventDirection.OUT
    PLACE_ORDER = 20, EventDirection.NEUTRAL
    TRANSFER = 21, EventDirection.NEUTRAL
    CLAIM_REWARD = 22, EventDirection.IN
    LIQUIDATION_REWARD = 23, EventDirection.IN
    LIQUIDATION_LOSS = 24, EventDirection.OUT
    INFORMATIONAL = 25, EventDirection.NEUTRAL
    CANCEL_ORDER = 26, EventDirection.IN
    REFUND = 27, EventDirection.IN
    FEE = 28, EventDirection.OUT
    MEV_REWARD = 29, EventDirection.IN
    STAKING_REWARD = 30, EventDirection.IN
    CREATE_BLOCK = 31, EventDirection.IN
    CREATE_PROJECT = 32, EventDirection.NEUTRAL
    UPDATE_PROJECT = 33, EventDirection.NEUTRAL
    APPLY = 34, EventDirection.NEUTRAL

    @property
    def direction(self) -> EventDirection:
        return self.value[1]

    def __str__(self) -> str:
        return ' '.join(word.lower() for word in self.name.split('_'))  # pylint: disable=no-member

    def serialize(self) -> str:
        return str(self)
