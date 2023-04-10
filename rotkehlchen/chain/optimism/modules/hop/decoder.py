from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.decoding.constants import CPT_HOP, HOP_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails, EventCategory
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_HETH_OPT, A_WETH_OPT
from rotkehlchen.types import ChecksumEvmAddress, DecoderEventMappingType
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator

ETH_BRIDGE = string_to_evm_address('0x83f6244Bd87662118d96D9a6D44f09dffF14b30E')
ETH_WRAPPER = string_to_evm_address('0x86cA30bEF97fB651b8d866D45503684b90cb3312')

TRANSFER_FROM_L1_COMPLETED = b'2\tX\x17i0\x80N\xb6l#C\xc74?\xc06}\xc1bIY\x0c\x0f\x19W\x83\xbe\xe1\x99\xd0\x94'  # noqa: E501


class HopDecoder(DecoderInterface):

    def __init__(  # pylint: disable=super-init-not-called
            self,
            optimism_inquirer: 'OptimismInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=optimism_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.weth = A_WETH_OPT.resolve_to_evm_token()
        self.heth = A_HETH_OPT.resolve_to_evm_token()

    def _decode_receive_eth(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == TRANSFER_FROM_L1_COMPLETED:
            recipient = hex_or_bytes_to_address(context.tx_log.topics[1])
            if not self.base.is_tracked(recipient):
                return DEFAULT_DECODING_OUTPUT

            amount_raw = hex_or_bytes_to_int(context.tx_log.data[:32])
            heth_amount = token_normalized_value_decimals(amount_raw, 18)

            for event in context.decoded_events:
                if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and recipient == event.location_label and event.asset == A_ETH:  # noqa: E501
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.BRIDGE
                    event.counterparty = CPT_HOP
                    event.notes = f'Bridge {event.balance.amount} ETH via hop protocol'
                    event.extra_data = {'sent_amount': str(heth_amount)}
        else:
            # No event for a particular withdrawal is emitted, so we can't verify the recipient,
            # amount, etc. Just trying to find all ETH bridge events.
            for event in context.decoded_events:
                if (
                    event.address == ETH_WRAPPER and
                    event.asset == A_ETH and
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE
                ):
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.BRIDGE
                    event.counterparty = CPT_HOP
                    event.notes = f'Bridge {event.balance.amount} ETH via hop protocol'

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def possible_events(self) -> DecoderEventMappingType:
        return {CPT_HOP: {
            HistoryEventType.WITHDRAWAL: {
                HistoryEventSubType.BRIDGE: EventCategory.BRIDGE,
            },
        }}

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            ETH_BRIDGE: (self._decode_receive_eth,),
        }

    def counterparties(self) -> list[CounterpartyDetails]:
        return [HOP_CPT_DETAILS]
