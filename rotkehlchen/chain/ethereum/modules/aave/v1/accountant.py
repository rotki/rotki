from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List, cast

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.structures.base import (
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
    get_tx_event_type_identifier,
)
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.accounting.interfaces import ModuleAccountantInterface
from rotkehlchen.chain.ethereum.accounting.structures import TxEventSettings, TxMultitakeTreatment
from rotkehlchen.constants import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEthAddress

from ..constants import CPT_AAVE_V1

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot


class Aavev1Accountant(ModuleAccountantInterface):

    def reset(self) -> None:
        self.balances: Dict[ChecksumEthAddress, Dict[Asset, FVal]] = defaultdict(lambda: defaultdict(FVal))  # noqa: E501

    def _process_deposit(
            self,
            pot: 'AccountingPot',  # pylint: disable=unused-argument
            event: HistoryBaseEntry,
            other_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
    ) -> None:
        address = event.location_label
        if address is None:
            return
        self.balances[address][event.asset] += event.balance.amount  # type: ignore

    def _process_withdraw(
            self,
            pot: 'AccountingPot',
            event: HistoryBaseEntry,
            other_events: List[HistoryBaseEntry],
    ) -> None:
        if event.location_label is None:
            return
        address = cast(ChecksumEthAddress, event.location_label)
        withdraw_event = other_events[0]
        self.balances[address][withdraw_event.asset] += withdraw_event.balance.amount  # noqa: E501

        if self.balances[address][withdraw_event.asset] < ZERO:
            profit = abs(self.balances[address][withdraw_event.asset])
            pot.add_acquisition(
                event_type=AccountingEventType.TRANSACTION_EVENT,
                notes=f'Gained {profit} {withdraw_event.asset} from {CPT_AAVE_V1}',
                location=event.location,
                timestamp=event.get_timestamp_in_sec(),
                asset=withdraw_event.asset,
                amount=profit,
                taxable=True,
                extra_data={'tx_hash': event.event_identifier},
            )
            self.balances[address][withdraw_event.asset] = ZERO

    def event_settings(self, pot: 'AccountingPot') -> Dict[str, TxEventSettings]:  # pylint: disable=unused-argument  # noqa: E501
        """Being defined at function call time is fine since this function is called only once"""
        return {
            get_tx_event_type_identifier(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET, CPT_AAVE_V1): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='spend',
                take=2,
                multitake_treatment=TxMultitakeTreatment.SWAP,
                accountant_cb=self._process_deposit,
            ),
            get_tx_event_type_identifier(HistoryEventType.SPEND, HistoryEventSubType.RETURN_WRAPPED, CPT_AAVE_V1): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='spend',
                take=2,
                multitake_treatment=TxMultitakeTreatment.SWAP,
                accountant_cb=self._process_withdraw,
            ),
        }
