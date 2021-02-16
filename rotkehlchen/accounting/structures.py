import operator
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, DefaultDict, Dict, List, Optional

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import DeserializationError, InputError
from rotkehlchen.fval import FVal
from rotkehlchen.typing import AssetAmount, Location, Timestamp
from rotkehlchen.utils.misc import combine_dicts


class BalanceType(Enum):
    ASSET = 0
    LIABILITY = 1

    def __str__(self) -> str:
        if self == BalanceType.ASSET:
            return 'asset'
        if self == BalanceType.LIABILITY:
            return 'liability'
        # else
        raise AssertionError(f'Invalid value {self} for BalanceType')

    @staticmethod
    def deserialize_from_db(value: str) -> 'BalanceType':
        if value == 'A':
            return BalanceType.ASSET
        if value == 'B':
            return BalanceType.LIABILITY
        # else
        raise DeserializationError(f'Encountered unknown BalanceType value {value} in the DB')

    def serialize_for_db(self) -> str:
        if self == BalanceType.ASSET:
            return 'A'
        if self == BalanceType.LIABILITY:
            return 'B'
        # else
        raise AssertionError(f'Invalid value {self} for BalanceType')


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


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class AssetBalance:
    asset: Asset
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


class DefiEventType(Enum):
    DSR_EVENT = 0
    MAKERDAO_VAULT_EVENT = auto()
    AAVE_EVENT = auto()
    YEARN_VAULTS_EVENT = auto()
    ADEX_EVENT = auto()
    COMPOUND_EVENT = auto()

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
        # else
        raise RuntimeError(f'Corrupt value {self} for DefiEventType -- Should never happen')


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DefiEvent:
    timestamp: Timestamp
    wrapped_event: Any
    event_type: DefiEventType
    got_asset: Optional[Asset]
    got_balance: Optional[Balance]
    spent_asset: Optional[Asset]
    spent_balance: Optional[Balance]
    pnl: Optional[List[AssetBalance]]
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
    assets: DefaultDict[Asset, Balance] = field(default_factory=lambda: defaultdict(Balance))
    liabilities: DefaultDict[Asset, Balance] = field(default_factory=lambda: defaultdict(Balance))

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


class LedgerActionType(Enum):
    INCOME = 0
    EXPENSE = 1
    LOSS = 2
    DIVIDENDS_INCOME = 3
    DONATION_RECEIVED = 4
    AIRDROP = 5
    GIFT = 6
    GRANT = 7

    def serialize(self) -> str:
        return str(self)

    def __str__(self) -> str:
        if self == LedgerActionType.INCOME:
            return 'income'
        if self == LedgerActionType.EXPENSE:
            return 'expense'
        if self == LedgerActionType.LOSS:
            return 'loss'
        if self == LedgerActionType.DIVIDENDS_INCOME:
            return 'dividends income'
        if self == LedgerActionType.DONATION_RECEIVED:
            return 'donation received'
        if self == LedgerActionType.AIRDROP:
            return 'airdrop'
        if self == LedgerActionType.GIFT:
            return 'gift'
        if self == LedgerActionType.GRANT:
            return 'grant'

        # else
        raise RuntimeError(f'Corrupt value {self} for LedgerActionType -- Should never happen')

    def serialize_for_db(self) -> str:
        if self == LedgerActionType.INCOME:
            return 'A'
        if self == LedgerActionType.EXPENSE:
            return 'B'
        if self == LedgerActionType.LOSS:
            return 'C'
        if self == LedgerActionType.DIVIDENDS_INCOME:
            return 'D'
        if self == LedgerActionType.DONATION_RECEIVED:
            return 'E'
        if self == LedgerActionType.AIRDROP:
            return 'F'
        if self == LedgerActionType.GIFT:
            return 'G'
        if self == LedgerActionType.GRANT:
            return 'H'

        # else
        raise RuntimeError(f'Corrupt value {self} for LedgerActionType -- Should never happen')

    def is_profitable(self) -> bool:
        return self in (
            LedgerActionType.INCOME,
            LedgerActionType.DIVIDENDS_INCOME,
            LedgerActionType.DONATION_RECEIVED,
            LedgerActionType.AIRDROP,
            LedgerActionType.GIFT,
            LedgerActionType.GRANT,
        )


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class LedgerAction:
    """Represents an income/loss/expense for accounting purposes"""
    identifier: int  # the unique id of the action and DB primary key
    timestamp: Timestamp
    action_type: LedgerActionType
    location: Location
    amount: AssetAmount
    asset: Asset
    link: str
    notes: str

    def serialize(self) -> Dict[str, Any]:
        return {
            'identifier': self.identifier,
            'timestamp': self.timestamp,
            'action_type': str(self.action_type),
            'location': str(self.location),
            'amount': str(self.amount),
            'asset': self.asset.identifier,
            'link': self.link,
            'notes': self.notes,
        }

    def is_profitable(self) -> bool:
        return self.action_type.is_profitable()


class ActionType(Enum):
    TRADE = 0
    ASSET_MOVEMENT = 1
    ETHEREUM_TX = 2
    LEDGER_ACTION = 3

    def __str__(self) -> str:
        if self == ActionType.TRADE:
            return 'trade'
        if self == ActionType.ASSET_MOVEMENT:
            return 'asset movement'
        if self == ActionType.ETHEREUM_TX:
            return 'ethereum transaction'
        if self == ActionType.LEDGER_ACTION:
            return 'ledger action'

        # else
        raise RuntimeError(f'Corrupt value {self} for ActionType -- Should never happen')

    def serialize_for_db(self) -> str:
        if self == ActionType.TRADE:
            return 'A'
        if self == ActionType.ASSET_MOVEMENT:
            return 'B'
        if self == ActionType.ETHEREUM_TX:
            return 'C'
        if self == ActionType.LEDGER_ACTION:
            return 'D'

        # else
        raise RuntimeError(f'Corrupt value {self} for ActionType -- Should never happen')
