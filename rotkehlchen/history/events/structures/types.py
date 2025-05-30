from enum import Enum, auto
from typing import Any, Literal, NamedTuple

from rotkehlchen.utils.mixins.enums import SerializableEnumNameMixin

EVM_EVENT_FIELDS = tuple[
    bytes,          # tx_hash
    str | None,  # counterparty
    str | None,  # product
    str | None,  # address
]


EVM_EVENT_DB_TUPLE_READ = tuple[
    int,            # identifier
    str,            # event_identifier
    int,            # sequence_index
    int,            # timestamp
    str,            # location
    str | None,  # location label
    str,            # asset
    str,            # amount
    str | None,  # notes
    str,            # type
    str,            # subtype
    str | None,     # extra_data
    int,            # ignored
    bytes,          # tx_hash
    str,            # address
    str | None,  # counterparty
    str | None,  # product
]


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
    FAIL = auto()
    LOSS = auto()
    MINT = auto()
    BURN = auto()
    MULTI_TRADE = auto()


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
    ATTEST = auto()
    PAYMENT = auto()
    GRANT = auto()
    INTEREST = auto()
    CASHBACK = auto()
    HACK = auto()
    CLAWBACK = auto()
    DEPOSIT_FOR_WRAPPED = auto()
    REDEEM_WRAPPED = auto()
    CONSOLIDATE = auto()
    DELEGATE = auto()
    LIQUIDITY_PROVISION_LOSS = auto()

    def serialize_or_none(self) -> str | None:
        return self.serialize()


class EventDirection(SerializableEnumNameMixin):
    """Describes the direction of an asset's movement (to the user, from the user or neutral)"""
    IN = auto()
    OUT = auto()
    NEUTRAL = auto()


class EventCategoryDetails(NamedTuple):
    label: str
    icon: str
    color: Literal['success', 'error'] | None = None

    def serialize(self) -> dict[str, Any]:
        result = {'label': self.label, 'icon': self.icon}
        if self.color is not None:
            result['color'] = self.color
        return result


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
    UPDATE = 33, EventDirection.NEUTRAL
    APPLY = 34, EventDirection.NEUTRAL
    STAKE_DEPOSIT = 35, EventDirection.OUT
    UNSTAKE = 36, EventDirection.IN
    ATTEST = 37, EventDirection.NEUTRAL
    STAKE_EXIT = 38, EventDirection.IN
    FAIL = 39, EventDirection.OUT
    PAY = 40, EventDirection.OUT
    RECEIVE_PAYMENT = 41, EventDirection.IN
    RECEIVE_GRANT = 42, EventDirection.IN
    INTEREST = 43, EventDirection.IN
    CEX_DEPOSIT = 44, EventDirection.IN
    CEX_WITHDRAWAL = 45, EventDirection.OUT
    CASHBACK = 46, EventDirection.IN
    HACK_LOSS = 47, EventDirection.OUT
    CLAWBACK = 48, EventDirection.OUT
    MINT_NFT = 49, EventDirection.IN
    BURN_NFT = 50, EventDirection.OUT
    COMBINE = 51, EventDirection.NEUTRAL
    DELEGATE = 52, EventDirection.NEUTRAL
    LOSS = 53, EventDirection.OUT
    LIQUIDITY_PROVISION_LOSS = 54, EventDirection.OUT

    @property
    def direction(self) -> EventDirection:
        return self.value[1]

    def __str__(self) -> str:
        return ' '.join(word.lower() for word in self.name.split('_'))  # pylint: disable=no-member

    def serialize(self) -> str:
        return str(self)
