import operator
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Callable, DefaultDict, Dict, Iterator, List, Optional, Tuple

from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import DeserializationError, InputError
from rotkehlchen.fval import FVal
from rotkehlchen.types import Location, Timestamp, TimestampMS
from rotkehlchen.utils.misc import combine_dicts, timestamp_to_date, ts_ms_to_sec
from rotkehlchen.utils.mixins.dbenum import DBEnumMixIn
from rotkehlchen.utils.mixins.serializableenum import SerializableEnumMixin

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot


class BalanceType(DBEnumMixIn):
    ASSET = 1
    LIABILITY = 2


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class Balance:
    amount: FVal = ZERO
    usd_value: FVal = ZERO

    @property
    def usd_rate(self) -> FVal:
        """How many $ 1 unit of balance is worth"""
        if self.amount == ZERO:
            return ZERO

        return self.usd_value / self.amount

    def serialize(self) -> Dict[str, str]:
        return {'amount': str(self.amount), 'usd_value': str(self.usd_value)}

    def to_dict(self) -> Dict[str, FVal]:
        return {'amount': self.amount, 'usd_value': self.usd_value}

    def __add__(self, other: Any) -> 'Balance':
        other = _evaluate_balance_input(other, 'addition')
        return Balance(
            amount=self.amount + other.amount,
            usd_value=self.usd_value + other.usd_value,
        )

    def __radd__(self, other: Any) -> 'Balance':
        if other == 0:
            return self

        other = _evaluate_balance_input(other, 'addition')
        return Balance(
            amount=self.amount + other.amount,
            usd_value=self.usd_value + other.usd_value,
        )

    def __sub__(self, other: Any) -> 'Balance':
        other = _evaluate_balance_input(other, 'subtraction')
        return Balance(
            amount=self.amount - other.amount,
            usd_value=self.usd_value - other.usd_value,
        )

    def __neg__(self) -> 'Balance':
        return Balance(amount=-self.amount, usd_value=-self.usd_value)

    def __abs__(self) -> 'Balance':
        return Balance(amount=abs(self.amount), usd_value=abs(self.usd_value))


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class AssetBalance:
    asset: 'Asset'
    balance: Balance

    @property
    def amount(self) -> FVal:
        return self.balance.amount

    @property
    def usd_value(self) -> FVal:
        return self.balance.usd_value

    def serialize(self) -> Dict[str, str]:
        result = self.balance.serialize()
        result['asset'] = self.asset.identifier
        return result

    def to_dict(self) -> Dict[str, Any]:
        result = self.balance.to_dict()
        result['asset'] = self.asset  # type: ignore
        return result

    def _evaluate_other_input(self, other: Any) -> None:
        if not isinstance(other, AssetBalance):
            raise TypeError(f'AssetBalance can not interact with {type(other)}')

        if self.asset != other.asset:
            raise TypeError(
                f'Tried to add {self.asset.identifier} balance to '
                f'{other.asset.identifier} balance',
            )

    def __add__(self, other: Any) -> 'AssetBalance':
        self._evaluate_other_input(other)
        new_balance = self.balance + other.balance
        return AssetBalance(asset=self.asset, balance=new_balance)

    def __sub__(self, other: Any) -> 'AssetBalance':
        self._evaluate_other_input(other)
        new_balance = self.balance - other.balance
        return AssetBalance(asset=self.asset, balance=new_balance)

    def __neg__(self) -> 'AssetBalance':
        return AssetBalance(asset=self.asset, balance=-self.balance)

    def serialize_for_db(self) -> Tuple[str, str, str]:
        return (self.asset.identifier, str(self.amount), str(self.usd_value))


class DefiEventType(Enum):
    DSR_EVENT = 0
    MAKERDAO_VAULT_EVENT = auto()
    AAVE_EVENT = auto()
    YEARN_VAULTS_EVENT = auto()
    ADEX_EVENT = auto()
    COMPOUND_EVENT = auto()
    ETH2_EVENT = auto()
    LIQUITY = auto()

    def __str__(self) -> str:
        if self == DefiEventType.DSR_EVENT:
            return 'MakerDAO DSR event'
        if self == DefiEventType.MAKERDAO_VAULT_EVENT:
            return 'MakerDAO vault event'
        if self == DefiEventType.AAVE_EVENT:
            return 'Aave event'
        if self == DefiEventType.YEARN_VAULTS_EVENT:
            return 'Yearn vault event'
        if self == DefiEventType.ADEX_EVENT:
            return 'AdEx event'
        if self == DefiEventType.COMPOUND_EVENT:
            return 'Compound event'
        if self == DefiEventType.ETH2_EVENT:
            return 'ETH2 event'
        if self == DefiEventType.LIQUITY:
            return 'Liquity event'
        # else
        raise RuntimeError(f'Corrupt value {self} for DefiEventType -- Should never happen')


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DefiEvent(AccountingEventMixin):
    timestamp: Timestamp
    wrapped_event: Any
    event_type: DefiEventType
    got_asset: Optional['Asset']
    got_balance: Optional[Balance]
    spent_asset: Optional['Asset']
    spent_balance: Optional[Balance]
    pnl: Optional[List[AssetBalance]]
    # If this is true then both got and spent asset count in cost basis
    # So it will count as if you got asset at given amount and price of timestamp
    # and spent asset at given amount and price of timestamp
    count_spent_got_cost_basis: bool
    tx_hash: Optional[str] = None

    def __str__(self) -> str:
        """Default string constructor"""
        result = str(self.wrapped_event)
        if self.tx_hash is not None:
            result += f' {self.tx_hash}'
        return result

    def to_string(self, timestamp_converter: Callable[[Timestamp], str]) -> str:
        """A customizable string constructor"""
        result = str(self)
        result += f' at {timestamp_converter(self.timestamp)}'
        return result

    # -- Methods of AccountingEventMixin

    def get_timestamp(self) -> Timestamp:
        return self.timestamp

    @staticmethod
    def get_accounting_event_type() -> AccountingEventType:
        return AccountingEventType.DEFI_EVENT

    def get_identifier(self) -> str:
        return self.__str__()

    def get_assets(self) -> List[Asset]:
        assets = set()
        if self.got_asset is not None:
            assets.add(self.got_asset)
        if self.spent_asset is not None:
            assets.add(self.spent_asset)
        if self.pnl is not None:
            for entry in self.pnl:
                assets.add(entry.asset)

        return list(assets)


def _evaluate_balance_input(other: Any, operation: str) -> Balance:
    transformed_input = other
    if isinstance(other, dict):
        if len(other) == 2 and 'amount' in other and 'usd_value' in other:
            try:
                amount = FVal(other['amount'])
                usd_value = FVal(other['usd_value'])
            except (ValueError, KeyError) as e:
                raise InputError(
                    f'Found valid dict object but with invalid values during Balance {operation}',
                ) from e
            transformed_input = Balance(amount=amount, usd_value=usd_value)
        else:
            raise InputError(f'Found invalid dict object during Balance {operation}')
    elif not isinstance(other, Balance):
        raise InputError(f'Found a {type(other)} object during Balance {operation}')

    return transformed_input


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class BalanceSheet:
    assets: DefaultDict['Asset', Balance] = field(default_factory=lambda: defaultdict(Balance))
    liabilities: DefaultDict['Asset', Balance] = field(default_factory=lambda: defaultdict(Balance))  # noqa: E501

    def copy(self) -> 'BalanceSheet':
        return BalanceSheet(assets=self.assets.copy(), liabilities=self.liabilities.copy())

    def serialize(self) -> Dict[str, Dict]:
        return {
            'assets': {k.serialize(): v.serialize() for k, v in self.assets.items()},
            'liabilities': {k: v.serialize() for k, v in self.liabilities.items()},
        }

    def to_dict(self) -> Dict[str, Dict]:
        return {
            'assets': {k: v.to_dict() for k, v in self.assets.items()},
            'liabilities': {k: v.to_dict() for k, v in self.liabilities.items()},
        }

    def __add__(self, other: Any) -> 'BalanceSheet':
        other = _evaluate_balance_sheet_input(other, 'addition')
        return BalanceSheet(
            assets=combine_dicts(self.assets, other.assets, op=operator.add),
            liabilities=combine_dicts(self.liabilities, other.liabilities, op=operator.add),
        )

    def __radd__(self, other: Any) -> 'BalanceSheet':
        if other == 0:
            return self

        other = _evaluate_balance_sheet_input(other, 'addition')
        return BalanceSheet(
            assets=self.assets + other.assets,
            liabilities=self.liabilities + other.liabilities,
        )

    def __sub__(self, other: Any) -> 'BalanceSheet':
        other = _evaluate_balance_sheet_input(other, 'subtraction')
        return BalanceSheet(
            assets=combine_dicts(self.assets, other.assets, op=operator.sub),
            liabilities=combine_dicts(self.liabilities, other.liabilities, op=operator.sub),
        )


def _evaluate_balance_sheet_input(other: Any, operation: str) -> BalanceSheet:
    transformed_input = other
    if isinstance(other, dict):
        if len(other) == 2 and 'assets' in other and 'liabilities' in other:
            try:
                assets = defaultdict(Balance)
                liabilities = defaultdict(Balance)
                for asset, entry in other['assets'].items():
                    assets[asset] = _evaluate_balance_input(entry, operation)
                for asset, entry in other['liabilities'].items():
                    liabilities[asset] = _evaluate_balance_input(entry, operation)
            except InputError as e:
                raise InputError(
                    f'Found valid dict object but with invalid values '
                    f'during BalanceSheet {operation}',
                ) from e
            transformed_input = BalanceSheet(assets=assets, liabilities=liabilities)
        else:
            raise InputError(f'Found invalid dict object during BalanceSheet {operation}')
    elif not isinstance(other, BalanceSheet):
        raise InputError(f'Found a {type(other)} object during BalanceSheet {operation}')

    return transformed_input


class ActionType(DBEnumMixIn):
    TRADE = 1
    ASSET_MOVEMENT = 2
    ETHEREUM_TRANSACTION = 3
    LEDGER_ACTION = 4


class HistoryEventType(SerializableEnumMixin):
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


class HistoryEventSubType(SerializableEnumMixin):
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
    GOVERNANCE_PROPOSE = auto()
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

    def serialize_or_none(self) -> Optional[str]:
        """Serializes the subtype but for the subtype None it returns None"""
        if self == HistoryEventSubType.NONE:
            return None

        return self.serialize()


HISTORY_EVENT_DB_TUPLE_READ = Tuple[
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
    Optional[str],  # counterparty
]

HISTORY_EVENT_DB_TUPLE_WRITE = Tuple[
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
    Optional[str],  # counterparty
]


def get_tx_event_type_identifier(event_type: HistoryEventType, event_subtype: HistoryEventSubType, counterparty: str) -> str:  # noqa: E501
    return str(event_type) + '__' + str(event_subtype) + '__' + counterparty


CPT_GAS = 'gas'
TX_TYPE_IDENTIFIER_TO_PNL_NAME = {
    str(HistoryEventType.SPEND) + '__' + str(HistoryEventSubType.FEE) + '__' + CPT_GAS: 'ethereum_transaction_gas_costs',  # noqa: E501
}


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class HistoryBaseEntry(AccountingEventMixin):
    """
    Intended to be the base unit of any type of accounting. All trades, deposits,
    swaps etc. are going to be made up of multiple HistoryBaseEntry
    """
    event_identifier: str  # identifier shared between related events
    sequence_index: int  # When this transaction was executed relative to other related events
    timestamp: TimestampMS
    location: Location
    event_type: HistoryEventType
    event_subtype: HistoryEventSubType
    asset: Asset
    balance: Balance
    # location_label is a string field that allows to provide more information about the location.
    # When we use this structure in blockchains can be used to specify addresses for example.
    # currently we use to identify the exchange name assigned by the user.
    location_label: Optional[str] = None
    notes: Optional[str] = None
    # identifier for counterparty.
    # For a send it's the target
    # For a receive it's the sender
    # For bridged transfer it's the bridge's network identifier
    # For a protocol interaction it's the protocol.
    counterparty: Optional[str] = None
    identifier: Optional[int] = None
    # this is not serialized -- contains data used only during processing
    extras: Optional[Dict] = None

    def serialize_for_db(self) -> HISTORY_EVENT_DB_TUPLE_WRITE:
        return (
            self.event_identifier,
            self.sequence_index,
            int(self.timestamp),
            self.location.serialize_for_db(),
            self.location_label,
            self.asset.identifier,
            str(self.balance.amount),
            str(self.balance.usd_value),
            self.notes,
            self.event_type.serialize(),
            self.event_subtype.serialize(),
            self.counterparty,
        )

    @classmethod
    def deserialize_from_db(cls, entry: HISTORY_EVENT_DB_TUPLE_READ) -> 'HistoryBaseEntry':
        """May raise:
        - DeserializationError
        - UnknownAsset
        """
        try:
            return HistoryBaseEntry(
                identifier=entry[0],
                event_identifier=entry[1],
                sequence_index=entry[2],
                timestamp=TimestampMS(entry[3]),
                location=Location.deserialize_from_db(entry[4]),
                location_label=entry[5],
                # Setting incomplete data to true since we save all history events,
                # regardless of the type of token that it may involve
                asset=Asset(entry[6], form_with_incomplete_data=True),
                balance=Balance(
                    amount=FVal(entry[7]),
                    usd_value=FVal(entry[8]),
                ),
                notes=entry[9],
                event_type=HistoryEventType.deserialize(entry[10]),
                event_subtype=HistoryEventSubType.deserialize(entry[11]),
                counterparty=entry[12],
            )
        except ValueError as e:
            raise DeserializationError(
                f'Failed to read FVal value from database history event with '
                f'event identifier {entry[1]}. {str(e)}',
            ) from e

    def serialize(self) -> Dict[str, Any]:
        return {
            'identifier': self.identifier,
            'event_identifier': self.event_identifier,
            'sequence_index': self.sequence_index,
            'timestamp': ts_ms_to_sec(self.timestamp),  # serialize to api in seconds MS
            'location': str(self.location),
            'asset': self.asset.identifier,
            'balance': self.balance.serialize(),
            'event_type': self.event_type.serialize(),
            'event_subtype': self.event_subtype.serialize_or_none(),
            'location_label': self.location_label,
            'notes': self.notes,
            'counterparty': self.counterparty,
        }

    def __str__(self) -> str:
        return (
            f'{self.event_subtype} event at {self.location} and time '
            f'{timestamp_to_date(ts_ms_to_sec(self.timestamp))} using {self.asset}'
        )

    def get_timestamp_in_sec(self) -> Timestamp:
        return ts_ms_to_sec(self.timestamp)

    def get_type_identifier(self) -> str:
        """A unique type identifier for known event types"""
        identifier = str(self.event_type) + '__' + str(self.event_subtype)
        if self.counterparty and not self.counterparty.startswith('0x'):
            identifier += '__' + self.counterparty

        return identifier

    # -- Methods of AccountingEventMixin

    def get_timestamp(self) -> Timestamp:
        return self.get_timestamp_in_sec()

    @staticmethod
    def get_accounting_event_type() -> AccountingEventType:
        return AccountingEventType.HISTORY_BASE_ENTRY

    def should_ignore(self, ignored_ids_mapping: Dict[ActionType, List[str]]) -> bool:
        if not self.event_identifier.startswith('0x'):
            return False

        ignored_ids = ignored_ids_mapping.get(ActionType.ETHEREUM_TRANSACTION, [])
        return self.event_identifier in ignored_ids

    def get_identifier(self) -> str:
        assert self.identifier is not None, 'Should never be called without identifier'
        return str(self.identifier)

    def get_assets(self) -> List[Asset]:
        return [self.asset]

    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: Iterator['AccountingEventMixin'],  # pylint: disable=unused-argument
    ) -> int:
        if self.location == Location.KRAKEN:
            if (
                self.event_type != HistoryEventType.STAKING or
                self.event_subtype != HistoryEventSubType.REWARD
            ):
                return 1

            # otherwise it's kraken staking
            accounting.add_acquisition(
                event_type=AccountingEventType.STAKING,
                notes=f'Kraken {self.asset.symbol} staking',
                location=self.location,
                timestamp=self.get_timestamp_in_sec(),
                asset=self.asset,
                amount=self.balance.amount,
                taxable=True,
            )
            return 1
        # else it's a decoded transaction event and should be processed there
        return accounting.transactions.process(self, events_iterator)


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class StakingEvent:
    event_type: HistoryEventSubType
    asset: Asset
    balance: Balance
    timestamp: Timestamp
    location: Location

    @classmethod
    def from_history_base_entry(cls, event: HistoryBaseEntry) -> 'StakingEvent':
        """
        Read staking event from a history base entry.
        May raise:
        - DeserializationError
        """
        return StakingEvent(
            event_type=event.event_subtype,
            asset=event.asset,
            balance=event.balance,
            timestamp=ts_ms_to_sec(event.timestamp),
            location=event.location,
        )

    def serialize(self) -> Dict[str, Any]:
        data = {
            'event_type': self.event_type.serialize(),
            'asset': self.asset.identifier,
            'timestamp': self.timestamp,
            'location': str(self.location),
        }
        balance = abs(self.balance).serialize()
        return {**data, **balance}
