from collections import defaultdict
from collections.abc import Iterator
from typing import TYPE_CHECKING

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.chain.evm.accounting.interfaces import ModuleAccountantInterface
from rotkehlchen.chain.evm.accounting.structures import EventsAccountantCallback
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE_V2
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import get_event_type_identifier
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress


class Aavev2Accountant(ModuleAccountantInterface):
    """Accountant for Aave v2 protocol"""
    def reset(self) -> None:
        self.assets_borrowed: dict[tuple[ChecksumEvmAddress, Asset], FVal] = defaultdict(FVal)
        self.assets_supplied: dict[tuple[ChecksumEvmAddress, Asset], FVal] = defaultdict(FVal)

    def _process_borrow(
            self,
            pot: 'AccountingPot',  # pylint: disable=unused-argument
            event: 'EvmEvent',
            other_events: Iterator['EvmEvent'],  # pylint: disable=unused-argument
    ) -> int:
        self.assets_borrowed[string_to_evm_address(event.location_label), event.asset] += event.amount  # type: ignore[arg-type]  # location_label can't be None here  # noqa: E501
        return 1

    def _process_payback(
            self,
            pot: 'AccountingPot',
            event: 'EvmEvent',
            other_events: Iterator['EvmEvent'],  # pylint: disable=unused-argument
    ) -> int:
        """
        Process payback events. If the paid back amount is higher that the borrowed amount,
        a loss event is added to the accounting pot.
        """
        key = (string_to_evm_address(event.location_label), event.asset)  # type: ignore[arg-type]  # location_label can't be None here
        self.assets_borrowed[key] -= event.amount
        if self.assets_borrowed[key] < ZERO:
            loss = -1 * self.assets_borrowed[key]
            resolved_asset = event.asset.resolve_to_asset_with_symbol()
            pot.add_out_event(
                originating_event_id=event.identifier,
                event_type=AccountingEventType.TRANSACTION_EVENT,
                notes=f'Lost {loss} {resolved_asset.symbol} as debt during payback to Aave v2 loan for {event.location_label}',  # noqa: E501
                location=event.location,
                timestamp=event.get_timestamp_in_sec(),
                asset=event.asset,
                amount=loss,
                taxable=True,
                extra_data={'tx_ref': str(event.tx_ref)},
            )
            self.assets_borrowed[key] = ZERO
        return 1

    def _process_deposit(
            self,
            pot: 'AccountingPot',  # pylint: disable=unused-argument
            event: 'EvmEvent',
            other_events: Iterator['EvmEvent'],  # pylint: disable=unused-argument
    ) -> int:
        self.assets_supplied[string_to_evm_address(event.location_label), event.asset] += event.amount  # type: ignore[arg-type]  # location_label can't be None here  # noqa: E501
        return 1

    def _process_withdraw(
            self,
            pot: 'AccountingPot',
            event: 'EvmEvent',
            other_events: Iterator['EvmEvent'],  # pylint: disable=unused-argument
    ) -> int:
        """
        Process withdrawal events. If the withdrawn amount is higher that the deposited amount,
        a gain event is added to the accounting pot.
        """
        key = (string_to_evm_address(event.location_label), event.asset)  # type: ignore[arg-type]  # location_label can't be None here
        self.assets_supplied[key] -= event.amount
        if self.assets_supplied[key] < ZERO:
            gain = -1 * self.assets_supplied[key]
            resolved_asset = event.asset.resolve_to_asset_with_symbol()
            pot.add_in_event(
                event_type=AccountingEventType.TRANSACTION_EVENT,
                notes=f'Gained {gain} {resolved_asset.symbol} on Aave v2 as interest rate for {event.location_label}',  # noqa: E501
                location=event.location,
                timestamp=event.get_timestamp_in_sec(),
                asset=event.asset,
                amount=gain,
                taxable=True,
                extra_data={'tx_ref': str(event.tx_ref)},
            )
            self.assets_supplied[key] = ZERO
        return 1

    def event_callbacks(self) -> dict[int, tuple[int, EventsAccountantCallback]]:
        """Being defined at function call time is fine since this function is called only once"""
        return {
            get_event_type_identifier(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_FOR_WRAPPED, CPT_AAVE_V2): (1, self._process_deposit),  # noqa: E501
            get_event_type_identifier(HistoryEventType.WITHDRAWAL, HistoryEventSubType.REDEEM_WRAPPED, CPT_AAVE_V2): (1, self._process_withdraw),  # noqa: E501
            get_event_type_identifier(HistoryEventType.RECEIVE, HistoryEventSubType.GENERATE_DEBT, CPT_AAVE_V2): (1, self._process_borrow),  # noqa: E501
            get_event_type_identifier(HistoryEventType.SPEND, HistoryEventSubType.PAYBACK_DEBT, CPT_AAVE_V2): (1, self._process_payback),  # noqa: E501
        }
