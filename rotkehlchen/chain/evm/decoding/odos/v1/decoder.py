import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.abi import decode_event_data_abi_str
from rotkehlchen.chain.evm.decoding.odos.common import OdosCommonDecoderBase
from rotkehlchen.chain.evm.decoding.odos.v1.constants import CPT_ODOS_V1, SWAPPED_EVENT_ABI
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Odosv1DecoderBase(OdosCommonDecoderBase):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            router_address: ChecksumEvmAddress,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_address=router_address,
        )

    def _decode_v1_swap(self, context: 'DecoderContext') -> 'DecodingOutput':
        """Decodes swaps done using an Odos v1 router"""
        if context.tx_log.topics[0] != b'\xe8uh\xfeY4\xcbu$\xb9n\x16\xb2%\xee.~s\x8c\xcb\xb7\x06\xc7\xbe\xe5,\xe0{\xf06\x0ei':  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        try:
            # decode the swap event structure
            # https://github.com/odos-xyz/odos-router-v1/blob/main/OdosRouter.sol#L36
            _, decoded_data = decode_event_data_abi_str(context.tx_log, SWAPPED_EVENT_ABI)
        except DeserializationError as e:
            log.error(
                f'Failed to deserialize Odos event {context.tx_log=} at '
                f'{context.transaction} due to {e}',
            )
            return DEFAULT_DECODING_OUTPUT

        if not self.base.is_tracked(decoded_data[0]):
            return DEFAULT_DECODING_OUTPUT

        input_tokens = self.base.resolve_tokens_data(token_amounts=decoded_data[1], token_addresses=decoded_data[2])  # noqa: E501
        output_tokens = self.base.resolve_tokens_data(token_amounts=decoded_data[3], token_addresses=[data[0] for data in decoded_data[4]])  # noqa: E501
        return self.decode_swap(
            context=context,
            sender=decoded_data[0],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.router_address: (self._decode_v1_swap,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_ODOS_V1,
            label='Odos v1',
            image='odos.svg',
        ),)
