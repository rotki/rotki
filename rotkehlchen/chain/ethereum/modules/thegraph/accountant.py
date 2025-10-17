from collections import defaultdict
from collections.abc import Iterator
from typing import TYPE_CHECKING, cast

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.chain.evm.accounting.interfaces import ModuleAccountantInterface
from rotkehlchen.chain.evm.accounting.structures import EventsAccountantCallback
from rotkehlchen.chain.evm.decoding.thegraph.constants import CPT_THEGRAPH
from rotkehlchen.constants import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import get_event_type_identifier
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress


class ThegraphAccountant(ModuleAccountantInterface):
    def reset(self) -> None:
        self.assets_supplied: dict[ChecksumEvmAddress, FVal] = defaultdict(FVal)

    def _process_deposit(
            self,
            pot: 'AccountingPot',  # pylint: disable=unused-argument
            event: 'EvmEvent',
            other_events: Iterator['EvmEvent'],  # pylint: disable=unused-argument
    ) -> int:
        self.assets_supplied[event.location_label] += event.amount  # type: ignore[index]
        return 1

    def _process_withdraw(
            self,
            pot: 'AccountingPot',
            event: 'EvmEvent',
            other_events: Iterator['EvmEvent'],  # pylint: disable=unused-argument
    ) -> int:
        address = cast('ChecksumEvmAddress', event.location_label)
        self.assets_supplied[address] -= event.amount
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
                extra_data={'tx_ref': str(event.tx_ref)},
            )
            self.assets_supplied[address] = ZERO
        return 1

    def event_callbacks(self) -> dict[int, tuple[int, EventsAccountantCallback]]:
        return {
            get_event_type_identifier(HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET, CPT_THEGRAPH): (1, self._process_deposit),  # noqa: E501
            get_event_type_identifier(HistoryEventType.STAKING, HistoryEventSubType.REMOVE_ASSET, CPT_THEGRAPH): (1, self._process_withdraw),  # noqa: E501
        }
