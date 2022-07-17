from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List, cast

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.structures.base import HistoryBaseEntry, get_tx_event_type_identifier
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.accounting.interfaces import ModuleAccountantInterface
from rotkehlchen.chain.ethereum.accounting.structures import TxEventSettings, TxMultitakeTreatment
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress

from .constants import CPT_DSR, CPT_MIGRATION, CPT_VAULT

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot


class MakerdaoAccountant(ModuleAccountantInterface):

    def reset(self) -> None:
        self.vault_balances: Dict[str, FVal] = defaultdict(FVal)
        self.dsr_balances: Dict[ChecksumEvmAddress, FVal] = defaultdict(FVal)

    def _process_vault_dai_generation(
            self,
            pot: 'AccountingPot',  # pylint: disable=unused-argument
            event: HistoryBaseEntry,
            other_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
    ) -> None:
        cdp_id = event.extra_data['cdp_id']  # type: ignore  # this event should have extra data
        self.vault_balances[cdp_id] += event.balance.amount

    def _process_vault_dai_payback(
            self,
            pot: 'AccountingPot',  # pylint: disable=unused-argument
            event: HistoryBaseEntry,
            other_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
    ) -> None:
        cdp_id = event.extra_data['cdp_id']  # type: ignore  # this event should have extra_data
        self.vault_balances[cdp_id] -= event.balance.amount
        if self.vault_balances[cdp_id] < ZERO:
            loss = -1 * self.vault_balances[cdp_id]
            pot.add_spend(
                event_type=AccountingEventType.TRANSACTION_EVENT,
                notes=f'Lost {loss} DAI as debt during payback to CDP {cdp_id}',
                location=event.location,
                timestamp=event.get_timestamp_in_sec(),
                asset=A_DAI,
                amount=loss,
                taxable=True,
                extra_data={'tx_hash': event.serialized_event_identifier},
            )
            self.vault_balances[cdp_id] = ZERO

    def _process_dsr_deposit(
            self,
            pot: 'AccountingPot',  # pylint: disable=unused-argument
            event: HistoryBaseEntry,
            other_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
    ) -> None:
        address = cast(ChecksumEvmAddress, event.location_label)  # should always exist
        self.dsr_balances[address] += event.balance.amount

    def _process_dsr_withdraw(
            self,
            pot: 'AccountingPot',  # pylint: disable=unused-argument
            event: HistoryBaseEntry,
            other_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
    ) -> None:
        address = cast(ChecksumEvmAddress, event.location_label)  # should always exist
        self.dsr_balances[address] -= event.balance.amount
        if self.dsr_balances[address] < ZERO:
            profit = -1 * self.dsr_balances[address]
            pot.add_acquisition(
                event_type=AccountingEventType.TRANSACTION_EVENT,
                notes=f'Gained {profit} DAI from Makerdao DSR',
                location=event.location,
                timestamp=event.get_timestamp_in_sec(),
                asset=A_DAI,
                amount=profit,
                taxable=True,
                extra_data={'tx_hash': event.serialized_event_identifier},
            )
            self.dsr_balances[address] = ZERO

    def event_settings(self, pot: 'AccountingPot') -> Dict[str, TxEventSettings]:  # pylint: disable=unused-argument  # noqa: E501
        """Being defined at function call time is fine since this function is called only once"""
        # TODO: How can we count here loss from debt and gain from DSR? We need to keep state
        return {  # vault collateral deposit
            get_tx_event_type_identifier(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET, CPT_VAULT): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='spend',
                take=1,
            ),  # vault collateral withdraw
            get_tx_event_type_identifier(HistoryEventType.WITHDRAWAL, HistoryEventSubType.REMOVE_ASSET, CPT_VAULT): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='acquisition',
                take=1,
            ),  # payback DAI to vault
            get_tx_event_type_identifier(HistoryEventType.SPEND, HistoryEventSubType.PAYBACK_DEBT, CPT_VAULT): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='spend',
                take=1,
                accountant_cb=self._process_vault_dai_payback,
            ),  # generate DAI from vault
            get_tx_event_type_identifier(HistoryEventType.WITHDRAWAL, HistoryEventSubType.GENERATE_DEBT, CPT_VAULT): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='acquisition',
                take=1,
                accountant_cb=self._process_vault_dai_generation,
            ),  # Deposit DAI in the DSR
            get_tx_event_type_identifier(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET, CPT_DSR): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='spend',
                take=1,
                accountant_cb=self._process_dsr_deposit,
            ),  # Withdraw DAI from the DSR
            get_tx_event_type_identifier(HistoryEventType.WITHDRAWAL, HistoryEventSubType.REMOVE_ASSET, CPT_DSR): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='acquisition',
                take=1,
                accountant_cb=self._process_dsr_withdraw,
            ),  # Migrate SAI to DAI
            get_tx_event_type_identifier(HistoryEventType.MIGRATE, HistoryEventSubType.SPEND, CPT_MIGRATION): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='spend',
                take=2,
                multitake_treatment=TxMultitakeTreatment.SWAP,
            ),
        }
