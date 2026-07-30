from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.relay.constants import CPT_RELAY, RELAY_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.utils import make_bridge_extra_data
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
    from rotkehlchen.user_messages import MessagesAggregator


class RelayDecoder(EvmDecoderInterface):

    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
            solver_addresses: frozenset[ChecksumEvmAddress],
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.solver_addresses = solver_addresses

    def _decode_bridge_receive(
            self,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> list[EvmEvent]:
        if (
            len(transaction.input_data) != 32 or
            transaction.from_address not in self.solver_addresses or
            transaction.to_address is None
        ):
            return decoded_events

        for event in decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == self.node_inquirer.native_token and
                event.location_label == transaction.to_address and
                event.address == transaction.from_address
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_RELAY
                event.notes = (
                    f'Bridge {event.amount} {event.asset.symbol_or_name()} to '
                    f'{transaction.to_address} at {self.node_inquirer.chain_id.label()} via Relay'
                )
                event.extra_data = (event.extra_data or {}) | make_bridge_extra_data(
                    from_chain=None,
                    to_chain=self.node_inquirer.chain_id,
                    to_address=transaction.to_address,
                    transfer_id=transaction.input_data.hex(),
                )
                break

        return decoded_events

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return dict.fromkeys(self.solver_addresses, CPT_RELAY)

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_RELAY: [(0, self._decode_bridge_receive)]}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (RELAY_CPT_DETAILS,)
