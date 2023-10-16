from collections import defaultdict
from collections.abc import Iterator
from typing import TYPE_CHECKING, cast

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.structures.base import get_event_type_identifier
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.thegraph.constants import CPT_THEGRAPH
from rotkehlchen.chain.evm.accounting.interfaces import ModuleAccountantInterface
from rotkehlchen.chain.evm.accounting.structures import TxEventSettings
from rotkehlchen.constants import ZERO
from rotkehlchen.fval import FVal

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.accounting.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress


class ThegraphAccountant(ModuleAccountantInterface):
    def reset(self) -> None:
        self.assets_supplied: dict[ChecksumEvmAddress, FVal] = defaultdict(FVal)

    def _process_deposit(
            self,
            pot: 'AccountingPot',  # pylint: disable=unused-argument
            event: 'EvmEvent',
            other_events: Iterator['EvmEvent'],  # pylint: disable=unused-argument
    ) -> None:
        self.assets_supplied[event.location_label] += event.balance.amount  # type: ignore[index]

    def _process_withdraw(
            self,
            pot: 'AccountingPot',
            event: 'EvmEvent',
            other_events: Iterator['EvmEvent'],  # pylint: disable=unused-argument
    ) -> None:
        address = cast('ChecksumEvmAddress', event.location_label)
        self.assets_supplied[address] -= event.balance.amount
        if self.assets_supplied[address] < ZERO:
            gain = -1 * self.assets_supplied[address]
            resolved_asset = event.asset.resolve_to_asset_with_symbol()
            pot.add_in_event(
                event_type=AccountingEventType.TRANSACTION_EVENT,
                notes=f'Gained {gain} {resolved_asset.symbol} as delegation reward for {address}',
                location=event.location,
                timestamp=event.get_timestamp_in_sec(),
                asset=event.asset,
                amount=gain,
                taxable=True,
                extra_data={'tx_hash': event.tx_hash.hex()},
            )
            self.assets_supplied[address] = ZERO

    def event_settings(self, pot: 'AccountingPot') -> dict[int, TxEventSettings]:  # pylint: disable=unused-argument
        return {
            get_event_type_identifier(HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET, CPT_THEGRAPH): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                accountant_cb=self._process_deposit,
            ),
            get_event_type_identifier(HistoryEventType.SPEND, HistoryEventSubType.FEE, CPT_THEGRAPH): TxEventSettings(  # noqa: E501
                taxable=True,
                count_entire_amount_spend=True,
                count_cost_basis_pnl=pot.settings.include_crypto2crypto,
            ),
            get_event_type_identifier(HistoryEventType.STAKING, HistoryEventSubType.REMOVE_ASSET, CPT_THEGRAPH): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                accountant_cb=self._process_withdraw,
            ),
        }
