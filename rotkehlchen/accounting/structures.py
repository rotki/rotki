import operator
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, DefaultDict, Dict

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


class DefiEventType(Enum):
    DSR_LOAN_GAIN = 0
    MAKERDAO_VAULT_LOSS = 1
    AAVE_LOAN_INTEREST = 2
    COMPOUND_LOAN_INTEREST = 3
    COMPOUND_DEBT_REPAY = 4
    COMPOUND_LIQUIDATION_DEBT_REPAID = 5
    COMPOUND_LIQUIDATION_COLLATERAL_LOST = 6
    COMPOUND_REWARDS = 7
    YEARN_VAULTS_PNL = 8
    AAVE_LOSS = 9
    ADEX_STAKE_PROFIT = 10

    def __str__(self) -> str:
        if self == DefiEventType.DSR_LOAN_GAIN:
            return "DSR loan gain"
        if self == DefiEventType.MAKERDAO_VAULT_LOSS:
            return "Makerdao vault loss"
        if self == DefiEventType.AAVE_LOAN_INTEREST:
            return "Aave loan interest"
        if self == DefiEventType.AAVE_LOSS:
            return "Aave loss"
        if self == DefiEventType.COMPOUND_LOAN_INTEREST:
            return "Compound loan interest"
        if self == DefiEventType.COMPOUND_DEBT_REPAY:
            return "Compound debt repayment"
        if self == DefiEventType.COMPOUND_LIQUIDATION_DEBT_REPAID:
            return "Compound liquidation debt repayment"
        if self == DefiEventType.COMPOUND_LIQUIDATION_COLLATERAL_LOST:
            return "Compound liquidation collateral lost"
        if self == DefiEventType.COMPOUND_REWARDS:
            return "Compound rewards"
        if self == DefiEventType.YEARN_VAULTS_PNL:
            return "Yearn vaults profit/loss"
        if self == DefiEventType.ADEX_STAKE_PROFIT:
            return "AdEx staking profit"
        # else
        raise RuntimeError(f'Corrupt value {self} for DefiEventType -- Should never happen')

    def is_profitable(self) -> bool:
        return self in (
            DefiEventType.DSR_LOAN_GAIN,
            DefiEventType.AAVE_LOAN_INTEREST,
            DefiEventType.COMPOUND_LOAN_INTEREST,
            DefiEventType.COMPOUND_REWARDS,
            DefiEventType.COMPOUND_DEBT_REPAY,
            DefiEventType.YEARN_VAULTS_PNL,
            DefiEventType.ADEX_STAKE_PROFIT,
        )


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DefiEvent:
    timestamp: Timestamp
    event_type: DefiEventType
    asset: Asset
    amount: FVal

    def is_profitable(self) -> bool:
        return self.event_type.is_profitable()


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class Balance:
    amount: FVal = ZERO
    usd_value: FVal = ZERO

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

    def __sub__(self, other: Any) -> 'Balance':
        other = _evaluate_balance_input(other, 'subtraction')
        return Balance(
            amount=self.amount - other.amount,
            usd_value=self.usd_value - other.usd_value,
        )

    def __neg__(self) -> 'Balance':
        return Balance(amount=-self.amount, usd_value=-self.usd_value)


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
        # else
        raise RuntimeError(f'Corrupt value {self} for LedgerActionType -- Should never happen')

    def is_profitable(self) -> bool:
        return self in (
            LedgerActionType.INCOME,
            LedgerActionType.DIVIDENDS_INCOME,
            LedgerActionType.DONATION_RECEIVED,
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
