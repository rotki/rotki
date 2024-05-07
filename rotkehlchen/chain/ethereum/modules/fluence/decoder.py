import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import CLAIMED, CPT_FLUENCE, DEV_REWARD_DISTRIBUTOR

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class FluenceDecoder(DecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )

    def _decode_fluence_claim(self, context: DecoderContext) -> DecodingOutput:
        if not (
            context.tx_log.topics[0] == CLAIMED and
            self.base.is_tracked(user_address := hex_or_bytes_to_address(context.tx_log.data[0:32]))  # noqa: E501
        ):
            return DEFAULT_DECODING_OUTPUT

        amount = token_normalized_value_decimals(hex_or_bytes_to_int(context.tx_log.data[32:64]), 18)  # noqa: E501

        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.balance.amount == amount and event.location_label == user_address and event.asset.resolve_to_evm_token().evm_address == DEV_REWARD_DISTRIBUTOR:  # noqa: E501
                event.notes = f'Claim {event.balance.amount} FLT from Fluence dev rewards'
                event.counterparty = CPT_FLUENCE
                event.address = DEV_REWARD_DISTRIBUTOR
                break

        else:
            log.error(f'Could not find the FLT-drop transfer in {context.transaction.tx_hash.hex()}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            DEV_REWARD_DISTRIBUTOR: (self._decode_fluence_claim,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_FLUENCE, label='Fluence', image='fluence.png'),)
