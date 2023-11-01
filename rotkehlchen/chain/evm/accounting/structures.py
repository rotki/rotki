from collections.abc import Iterator
from enum import auto
from typing import TYPE_CHECKING, Any, Optional, Protocol, Union

from rotkehlchen.utils.mixins.enums import DBCharEnumMixIn

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.accounting.structures.evm_event import EvmEvent


class EventsAccountantCallback(Protocol):
    """Type of a Submodule's accountant callback"""
    def __call__(
            self,
            pot: 'AccountingPot',
            event: 'EvmEvent',
            other_events: Iterator['EvmEvent'],
    ) -> None:
        """
        Callback to be called by the accounting module.
        If the callback expects more than 1 events, it is supposed to iterate over the
        `other_events` iterator to get them.
        Note that events consumed by the callback from the iterator will not be re-processed later.
        """


class TxAccountingTreatment(DBCharEnumMixIn):
    SWAP = auto()
    SWAP_WITH_FEE = auto()


ACCOUNTING_SETTING_DB_TUPLE = tuple[
    int,  # taxable
    int,  # count_entire_amount_spend
    int,  # count_cost_basis_pnl
    Union[str, None],  # accounting_treatment
]


class BaseEventSettings:
    """Acounting settings for history base entry events"""
    def __init__(
            self,
            taxable: bool,
            count_entire_amount_spend: bool,
            count_cost_basis_pnl: bool,
            accounting_treatment: Optional[TxAccountingTreatment] = None,
    ):
        self.taxable = taxable
        self.count_entire_amount_spend = count_entire_amount_spend
        self.count_cost_basis_pnl = count_cost_basis_pnl
        self.accounting_treatment = accounting_treatment

    @classmethod
    def deserialize_from_db(cls, entry: ACCOUNTING_SETTING_DB_TUPLE) -> 'BaseEventSettings':
        return cls(
            taxable=bool(entry[0]),
            count_entire_amount_spend=bool(entry[1]),
            count_cost_basis_pnl=bool(entry[2]),
            accounting_treatment=TxAccountingTreatment.deserialize_from_db(entry[3]) if entry[3] else None,  # noqa: E501
        )

    def serialize_for_db(self) -> ACCOUNTING_SETTING_DB_TUPLE:
        return (
            self.taxable,
            self.count_entire_amount_spend,
            self.count_cost_basis_pnl,
            self.accounting_treatment.serialize_for_db() if self.accounting_treatment else None,
        )

    def serialize(self) -> dict[str, Any]:
        return {
            'taxable': {'value': self.taxable},
            'count_cost_basis_pnl': {'value': self.count_cost_basis_pnl},
            'count_entire_amount_spend': {'value': self.count_entire_amount_spend},
            'accounting_treatment': self.accounting_treatment,
        }

    def __hash__(self) -> int:
        return hash(f'{self.taxable}{self.count_entire_amount_spend}{self.count_cost_basis_pnl}{self.accounting_treatment!s}')  # noqa: E501

    def __eq__(self, other: object) -> bool:
        return hash(self) == hash(other)


class TxEventSettings(BaseEventSettings):
    """Accounting settings for EVM transaction events"""
    def __init__(
            self,
            taxable: bool,
            count_entire_amount_spend: bool,
            count_cost_basis_pnl: bool,
            accounting_treatment: Optional[TxAccountingTreatment] = None,
            accountant_cb: Optional[EventsAccountantCallback] = None,
    ):
        super().__init__(
            taxable=taxable,
            count_entire_amount_spend=count_entire_amount_spend,
            count_cost_basis_pnl=count_cost_basis_pnl,
            accounting_treatment=accounting_treatment,
        )
        self.accountant_cb = accountant_cb
