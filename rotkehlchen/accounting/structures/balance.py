import operator
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Self

from rotkehlchen.constants import ZERO
from rotkehlchen.errors.misc import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.utils.misc import combine_nested_dicts_inplace
from rotkehlchen.utils.mixins.enums import DBCharEnumMixIn

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset


class BalanceType(DBCharEnumMixIn):
    ASSET = 1
    LIABILITY = 2


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class Balance:
    amount: FVal = ZERO
    value: FVal = ZERO

    def serialize(self) -> dict[str, str]:
        return {
            'amount': str(self.amount),
            'value': str(self.value),
        }

    def to_dict(self) -> dict[str, FVal]:
        return {'amount': self.amount, 'value': self.value}

    def __add__(self, other: Any) -> 'Balance':
        other = _evaluate_balance_input(other, 'addition')
        return Balance(
            amount=self.amount + other.amount,
            value=self.value + other.value,
        )

    def __radd__(self, other: Any) -> 'Balance':
        if other == 0:
            return self

        other = _evaluate_balance_input(other, 'addition')
        return Balance(
            amount=self.amount + other.amount,
            value=self.value + other.value,
        )

    def __sub__(self, other: Any) -> 'Balance':
        other = _evaluate_balance_input(other, 'subtraction')
        return Balance(
            amount=self.amount - other.amount,
            value=self.value - other.value,
        )

    def __mul__(self, other: Any) -> 'Balance':
        if not isinstance(other, (int | FVal)):
            raise InputError(f'Tried to multiply balance with {type(other)}')

        return Balance(
            amount=self.amount * other,
            value=self.value * other,
        )

    def __neg__(self) -> 'Balance':
        return Balance(amount=-self.amount, value=-self.value)

    def __abs__(self) -> 'Balance':
        return Balance(amount=abs(self.amount), value=abs(self.value))


def _evaluate_balance_input(other: Any, operation: str) -> Balance:
    transformed_input = other
    if isinstance(other, dict):
        if len(other) == 2 and 'amount' in other and 'value' in other:
            try:
                amount = FVal(other['amount'])
                value = FVal(other['value'])
            except (ValueError, KeyError) as e:
                raise InputError(
                    f'Found valid dict object but with invalid values during Balance {operation}',
                ) from e
            transformed_input = Balance(amount=amount, value=value)
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
    def value(self) -> FVal:
        return self.balance.value

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
        return self.asset.identifier, str(self.amount), str(self.value)


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class BalanceSheet:
    assets: defaultdict['Asset', defaultdict[str, Balance]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(Balance)))  # noqa: E501
    liabilities: defaultdict['Asset', defaultdict[str, Balance]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(Balance)))  # noqa: E501

    def copy(self) -> 'BalanceSheet':
        return BalanceSheet(
            assets=defaultdict(lambda: defaultdict(Balance), {
                asset: defaultdict(Balance, balances.copy())
                for asset, balances in self.assets.items()
            }),
            liabilities=defaultdict(lambda: defaultdict(Balance), {
                asset: defaultdict(Balance, balances.copy())
                for asset, balances in self.liabilities.items()
            }),
        )

    def serialize(self) -> dict[str, dict]:
        return {
            'assets': {
                k.serialize(): {label: balance.serialize() for label, balance in v.items()}
                for k, v in self.assets.items()
            },
            'liabilities': {
                k.serialize(): {label: balance.serialize() for label, balance in v.items()}
                for k, v in self.liabilities.items()
            },
        }

    def to_dict(self) -> dict[str, dict]:
        return {
            'assets': {
                k: {label: balance.to_dict() for label, balance in v.items()}
                for k, v in self.assets.items()
            },
            'liabilities': {
                k: {label: balance.to_dict() for label, balance in v.items()}
                for k, v in self.liabilities.items()
            },
        }

    def _merged_with(self, other: 'BalanceSheet', op: Callable) -> 'BalanceSheet':
        """Return a new BalanceSheet combining self and other, without mutating either.

        Used by the non-augmented operators (+, -, sum) so that `a + b` does not alter `a`.
        """
        result = self.copy()
        combine_nested_dicts_inplace(a=result.assets, b=other.assets, op=op)
        combine_nested_dicts_inplace(a=result.liabilities, b=other.liabilities, op=op)
        return result

    def _merge_inplace(self, other: 'BalanceSheet', op: Callable) -> Self:
        """Merge other into self in place and return self.

        Used by the augmented operators (+=, -=); this is the fast path relied upon by the
        accumulation loops (e.g. recalculate_totals) and avoids copying the accumulator.
        """
        combine_nested_dicts_inplace(a=self.assets, b=other.assets, op=op)
        combine_nested_dicts_inplace(a=self.liabilities, b=other.liabilities, op=op)
        return self

    def __add__(self, other: Any) -> 'BalanceSheet':
        return self._merged_with(_evaluate_balance_sheet_input(other, 'addition'), operator.add)

    def __radd__(self, other: Any) -> 'BalanceSheet':
        if other == 0:  # identity element used by sum(); return a copy so the first
            return self.copy()  # element of the summed iterable is never mutated

        return self._merged_with(_evaluate_balance_sheet_input(other, 'addition'), operator.add)

    def __sub__(self, other: Any) -> 'BalanceSheet':
        return self._merged_with(_evaluate_balance_sheet_input(other, 'subtraction'), operator.sub)

    def __iadd__(self, other: Any) -> Self:
        return self._merge_inplace(_evaluate_balance_sheet_input(other, 'addition'), operator.add)

    def __isub__(self, other: Any) -> Self:
        return self._merge_inplace(
            _evaluate_balance_sheet_input(other, 'subtraction'), operator.sub,
        )


def _evaluate_balance_sheet_input(other: Any, operation: str) -> BalanceSheet:
    transformed_input = other
    if isinstance(other, dict):
        if len(other) == 2 and 'assets' in other and 'liabilities' in other:
            try:
                assets: defaultdict[Asset, defaultdict[str, Balance]] = defaultdict(lambda: defaultdict(Balance))  # noqa: E501
                liabilities: defaultdict[Asset, defaultdict[str, Balance]] = defaultdict(lambda: defaultdict(Balance))  # noqa: E501
                for asset, balance_entries in other['assets'].items():
                    for label, entry in balance_entries.items():
                        assets[asset][label] = _evaluate_balance_input(entry, operation)
                for asset, balance_entries in other['liabilities'].items():
                    for label, entry in balance_entries.items():
                        liabilities[asset][label] = _evaluate_balance_input(entry, operation)
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
