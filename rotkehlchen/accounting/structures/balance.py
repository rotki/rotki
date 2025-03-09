import operator
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from rotkehlchen.constants import ZERO
from rotkehlchen.errors.misc import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.utils.misc import combine_dicts
from rotkehlchen.utils.mixins.enums import DBCharEnumMixIn

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset


class BalanceType(DBCharEnumMixIn):
    ASSET = 1
    LIABILITY = 2


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class Balance:
    amount: FVal = ZERO
    usd_value: FVal = ZERO

    def serialize(self) -> dict[str, str]:
        return {'amount': str(self.amount), 'usd_value': str(self.usd_value)}

    def to_dict(self) -> dict[str, FVal]:
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

    def __mul__(self, other: Any) -> 'Balance':
        if not isinstance(other, (int, FVal)):
            raise InputError(f'Tried to multiply balance with {type(other)}')

        return Balance(
            amount=self.amount * other,
            usd_value=self.usd_value * other,
        )

    def __neg__(self) -> 'Balance':
        return Balance(amount=-self.amount, usd_value=-self.usd_value)

    def __abs__(self) -> 'Balance':
        return Balance(amount=abs(self.amount), usd_value=abs(self.usd_value))


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
class AssetBalance:
    asset: 'Asset'
    balance: Balance

    @property
    def amount(self) -> FVal:
        return self.balance.amount

    @property
    def usd_value(self) -> FVal:
        return self.balance.usd_value

    def serialize(self) -> dict[str, str]:
        result = self.balance.serialize()
        result['asset'] = self.asset.identifier
        return result

    def to_dict(self) -> dict[str, Any]:
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

    def serialize_for_db(self) -> tuple[str, str, str]:
        return (self.asset.identifier, str(self.amount), str(self.usd_value))


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class BalanceSheet:
    assets: defaultdict['Asset', Balance] = field(default_factory=lambda: defaultdict(Balance))
    liabilities: defaultdict['Asset', Balance] = field(default_factory=lambda: defaultdict(Balance))  # noqa: E501

    def copy(self) -> 'BalanceSheet':
        return BalanceSheet(assets=self.assets.copy(), liabilities=self.liabilities.copy())

    def serialize(self) -> dict[str, dict]:
        return {
            'assets': {k.serialize(): v.serialize() for k, v in self.assets.items()},
            'liabilities': {k: v.serialize() for k, v in self.liabilities.items()},
        }

    def to_dict(self) -> dict[str, dict]:
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
