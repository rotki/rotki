import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.abi import decode_event_data_abi_str
from rotkehlchen.chain.evm.decoding.odos.common import OdosCommonDecoderBase
from rotkehlchen.chain.evm.decoding.odos.v2.constants import CPT_ODOS_V2, SWAPMULTI_EVENT_ABI
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Odosv2DecoderBase(OdosCommonDecoderBase):
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

    def _decode_v2_swap(self, context: 'DecoderContext') -> 'EvmDecodingOutput':
        """Decodes swaps done using an Odos v2 router"""
        if context.tx_log.topics[0] == b'\x82>\xaf\x01\x00-sS\xfb\xca\xdb.\xa30\\\xc4o\xa3]y\x9c\xb0\x91HF\xd1\x85\xac\x06\xf8\xad\x05':  # swapCompact()  # noqa: E501
            # decode the single swap event structure
            # https://github.com/odos-xyz/odos-router-v2/blob/main/contracts/OdosRouterV2.sol#L64
            decoded_data: tuple[ChecksumEvmAddress, list[int], list[ChecksumEvmAddress], list[int], list[ChecksumEvmAddress]] = (  # noqa: E501
                bytes_to_address(context.tx_log.data[0:32]),  # sender
                [int.from_bytes(context.tx_log.data[32:64])],  # input amount
                [bytes_to_address(context.tx_log.data[64:96])],  # input token address
                [int.from_bytes(context.tx_log.data[96:128])],  # output amount
                [bytes_to_address(context.tx_log.data[128:160])],  # output token address
            )
        elif context.tx_log.topics[0] == b'}\x7f\xb05\x18%:\xe0\x19\x13Sf(\xb7\x8dm\x82\xe6>\x19\xb9C\xaa\xb5\xf4\x94\x83V\x02\x12Y\xbe':  # swapMultiCompact()  # noqa: E501
            try:
                # decode the multi swap event structure
                # https://github.com/odos-xyz/odos-router-v2/blob/main/contracts/OdosRouterV2.sol#L74
                _, decoded_data = decode_event_data_abi_str(context.tx_log, SWAPMULTI_EVENT_ABI)  # type: ignore[assignment]  # types are known from the ABI
            except DeserializationError as e:
                log.error(
                    f'Failed to deserialize Odos event {context.tx_log=} at '
                    f'{context.transaction} due to {e}',
                )
                return DEFAULT_EVM_DECODING_OUTPUT
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(decoded_data[0]):
            return DEFAULT_EVM_DECODING_OUTPUT

        input_tokens = self.base.resolve_tokens_data(token_amounts=decoded_data[1], token_addresses=decoded_data[2])  # noqa: E501
        output_tokens = self.base.resolve_tokens_data(token_amounts=decoded_data[3], token_addresses=decoded_data[4])  # noqa: E501
        return self.decode_swap(
            context=context,
            sender=decoded_data[0],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.router_address: (self._decode_v2_swap,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_ODOS_V2,
            label='Odos v2',
            image='odos.svg',
        ),)
