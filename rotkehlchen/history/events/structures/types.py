from enum import Enum, auto
from typing import Any, Literal, NamedTuple

from rotkehlchen.utils.mixins.enums import SerializableEnumNameMixin

# Represents common blockchain metadata fields.
CHAIN_EVENT_FIELDS_TYPE = tuple[
    bytes,  # tx_hash
    str | None,  # counterparty
    str | None,  # address
]

CHAIN_EVENT_DB_TUPLE_READ = tuple[
    int,            # identifier
    str,            # group_identifier
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
    MARGIN = auto()
    TRANSACTION_TO_SELF = auto()
    EXCHANGE_ADJUSTMENT = auto()
    EXCHANGE_TRANSFER = auto()


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
    BURN = auto()
    MESSAGE = auto()
    PROFIT = auto()
    LOSS = auto()
    DEPOSIT_TO_PROTOCOL = auto()
    WITHDRAW_FROM_PROTOCOL = auto()
    SPAM = auto()  # for spam/phishing transactions

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


class EventCategoryGroup(SerializableEnumNameMixin):
    """User-facing grouping for the verb picker. Each EventCategory belongs to one."""
    TRADE = auto()
    TRANSFER = auto()
    DEFI_DEPOSIT_WITHDRAW = auto()
    DEFI_BORROW_REPAY = auto()
    STAKING = auto()
    INCOME = auto()
    EXPENSE = auto()
    DONATION = auto()
    NFT = auto()
    BRIDGE = auto()
    CEX = auto()
    VALIDATOR = auto()
    GOVERNANCE = auto()
    APPROVAL = auto()
    LOSS = auto()
    OTHER = auto()


class EventCategoryGroupDetails(NamedTuple):
    icon: str
    order: int

    def serialize(self) -> dict[str, Any]:
        return {'icon': self.icon, 'order': self.order}


class EventCategory(Enum):
    """User friendly categories to classify combinations of event type and event subtype

    Can't use auto() yet cause has to be only thing in line.
    https://docs.python.org/3/library/enum.html#enum.auto

    From 3.11 and on we will be able to adjust.
    """
    SEND = 1, EventDirection.OUT, EventCategoryGroup.TRANSFER
    RECEIVE = 2, EventDirection.IN, EventCategoryGroup.TRANSFER
    SWAP_OUT = 3, EventDirection.OUT, EventCategoryGroup.TRADE
    SWAP_IN = 4, EventDirection.IN, EventCategoryGroup.TRADE
    MIGRATE_OUT = 5, EventDirection.OUT, EventCategoryGroup.TRANSFER
    MIGRATE_IN = 6, EventDirection.IN, EventCategoryGroup.TRANSFER
    APPROVAL = 7, EventDirection.NEUTRAL, EventCategoryGroup.APPROVAL
    DEPOSIT = 8, EventDirection.OUT, EventCategoryGroup.DEFI_DEPOSIT_WITHDRAW
    WITHDRAW = 9, EventDirection.IN, EventCategoryGroup.DEFI_DEPOSIT_WITHDRAW
    AIRDROP = 10, EventDirection.IN, EventCategoryGroup.INCOME
    BORROW = 11, EventDirection.IN, EventCategoryGroup.DEFI_BORROW_REPAY
    REPAY = 12, EventDirection.OUT, EventCategoryGroup.DEFI_BORROW_REPAY
    DEPLOY = 12, EventDirection.NEUTRAL, EventCategoryGroup.OTHER
    DEPLOY_WITH_SPEND = 13, EventDirection.OUT, EventCategoryGroup.EXPENSE
    BRIDGE_DEPOSIT = 14, EventDirection.OUT, EventCategoryGroup.BRIDGE
    BRIDGE_WITHDRAWAL = 15, EventDirection.IN, EventCategoryGroup.BRIDGE
    GOVERNANCE = 16, EventDirection.NEUTRAL, EventCategoryGroup.GOVERNANCE
    DONATE = 17, EventDirection.OUT, EventCategoryGroup.DONATION
    RECEIVE_DONATION = 18, EventDirection.IN, EventCategoryGroup.DONATION
    RENEW = 19, EventDirection.OUT, EventCategoryGroup.EXPENSE
    PLACE_ORDER = 20, EventDirection.NEUTRAL, EventCategoryGroup.TRADE
    TRANSFER = 21, EventDirection.NEUTRAL, EventCategoryGroup.TRANSFER
    CLAIM_REWARD = 22, EventDirection.IN, EventCategoryGroup.INCOME
    LIQUIDATION_REWARD = 23, EventDirection.IN, EventCategoryGroup.INCOME
    LIQUIDATION_LOSS = 24, EventDirection.OUT, EventCategoryGroup.LOSS
    INFORMATIONAL = 25, EventDirection.NEUTRAL, EventCategoryGroup.OTHER
    CANCEL_ORDER = 26, EventDirection.IN, EventCategoryGroup.TRADE
    REFUND = 27, EventDirection.IN, EventCategoryGroup.INCOME
    FEE = 28, EventDirection.OUT, EventCategoryGroup.EXPENSE
    MEV_REWARD = 29, EventDirection.IN, EventCategoryGroup.VALIDATOR
    STAKING_REWARD = 30, EventDirection.IN, EventCategoryGroup.INCOME
    CREATE_BLOCK = 31, EventDirection.IN, EventCategoryGroup.VALIDATOR
    CREATE_PROJECT = 32, EventDirection.NEUTRAL, EventCategoryGroup.OTHER
    UPDATE = 33, EventDirection.NEUTRAL, EventCategoryGroup.OTHER
    APPLY = 34, EventDirection.NEUTRAL, EventCategoryGroup.OTHER
    STAKE_DEPOSIT = 35, EventDirection.OUT, EventCategoryGroup.STAKING
    UNSTAKE = 36, EventDirection.IN, EventCategoryGroup.STAKING
    ATTEST = 37, EventDirection.NEUTRAL, EventCategoryGroup.VALIDATOR
    STAKE_EXIT = 38, EventDirection.IN, EventCategoryGroup.STAKING
    FAIL = 39, EventDirection.OUT, EventCategoryGroup.LOSS
    PAY = 40, EventDirection.OUT, EventCategoryGroup.EXPENSE
    RECEIVE_PAYMENT = 41, EventDirection.IN, EventCategoryGroup.INCOME
    RECEIVE_GRANT = 42, EventDirection.IN, EventCategoryGroup.INCOME
    INTEREST = 43, EventDirection.IN, EventCategoryGroup.INCOME
    CEX_DEPOSIT = 44, EventDirection.NEUTRAL, EventCategoryGroup.CEX
    CEX_WITHDRAWAL = 45, EventDirection.NEUTRAL, EventCategoryGroup.CEX
    CASHBACK = 46, EventDirection.IN, EventCategoryGroup.INCOME
    HACK_LOSS = 47, EventDirection.OUT, EventCategoryGroup.LOSS
    CLAWBACK = 48, EventDirection.OUT, EventCategoryGroup.LOSS
    MINT_NFT = 49, EventDirection.IN, EventCategoryGroup.NFT
    BURN = 50, EventDirection.OUT, EventCategoryGroup.LOSS
    COMBINE = 51, EventDirection.NEUTRAL, EventCategoryGroup.OTHER
    DELEGATE = 52, EventDirection.NEUTRAL, EventCategoryGroup.GOVERNANCE
    LOSS = 53, EventDirection.OUT, EventCategoryGroup.LOSS
    LIQUIDITY_PROVISION_LOSS = 54, EventDirection.OUT, EventCategoryGroup.LOSS
    RETURN = 55, EventDirection.OUT, EventCategoryGroup.DEFI_BORROW_REPAY
    MESSAGE = 56, EventDirection.NEUTRAL, EventCategoryGroup.OTHER
    ACCOUNT_DEPOSIT = 57, EventDirection.NEUTRAL, EventCategoryGroup.CEX
    ACCOUNT_WITHDRAWAL = 58, EventDirection.NEUTRAL, EventCategoryGroup.CEX
    PROFIT = 59, EventDirection.IN, EventCategoryGroup.INCOME
    SELF_TRANSACTION = 60, EventDirection.NEUTRAL, EventCategoryGroup.TRANSFER
    PROTOCOL_DEPOSIT = 61, EventDirection.NEUTRAL, EventCategoryGroup.DEFI_DEPOSIT_WITHDRAW
    PROTOCOL_WITHDRAWAL = 62, EventDirection.NEUTRAL, EventCategoryGroup.DEFI_DEPOSIT_WITHDRAW
    SPAM = 63, EventDirection.IN, EventCategoryGroup.OTHER

    @property
    def direction(self) -> EventDirection:
        return self.value[1]

    @property
    def group(self) -> EventCategoryGroup:
        return self.value[2]

    def __str__(self) -> str:
        return ' '.join(word.lower() for word in self.name.split('_'))  # pylint: disable=no-member

    def serialize(self) -> str:
        return str(self)
