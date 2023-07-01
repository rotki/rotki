from enum import auto
from typing import Optional

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
    EVM_TRANSACTION = 3
    LEDGER_ACTION = 4

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
    UNKNOWN = auto()
    # An informational event. For kraken entries it means an unknown event
    INFORMATIONAL = auto()
    MIGRATE = auto()
    RENEW = auto()


class HistoryEventSubType(SerializableEnumNameMixin):
    REWARD = 0
    DEPOSIT_ASSET = auto()  # deposit asset in a contract, for staking etc.
    REMOVE_ASSET = auto()  # remove asset from a contract. from staking etc.
    FEE = auto()
    SPEND = auto()
    RECEIVE = auto()
    APPROVE = auto()
    DEPLOY = auto()
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

    def serialize_or_none(self) -> Optional[str]:
        """Serializes the subtype but for the subtype None it returns None"""
        if self == HistoryEventSubType.NONE:
            return None

        return self.serialize()
