from abc import ABCMeta
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.airdrops import match_airdrop_claim
from rotkehlchen.chain.evm.decoding.cowswap.constants import CPT_COWSWAP
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

CLAIMED = b'\xd46\xe9\x97=\x1eD\xd4\r\xb4\xd4\x11\x9e<w<\xad\xb12;&9\x81\x96\x8c\x14\xd3\xd1\x91\xc0\xe1H'  # noqa: E501


class CowswapAirdropDecoder(DecoderInterface, metaclass=ABCMeta):
    """Common decoder for cowswap airdrops in gnosis and ethereum"""
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            vcow: 'Asset',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.vcow = vcow.resolve_to_evm_token()

    def _decode_cow_claim(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != CLAIMED:
            return DEFAULT_DECODING_OUTPUT

        raw_amount = hex_or_bytes_to_int(context.tx_log.data[128:160])
        amount = asset_normalized_value(amount=raw_amount, asset=self.vcow)
        for event in context.decoded_events:
            if match_airdrop_claim(
                event,
                user_address=hex_or_bytes_to_address(context.tx_log.data[64:96]),
                amount=amount,
                asset=self.vcow,
                counterparty=CPT_COWSWAP,
            ):
                break

        return DEFAULT_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return {
            self.vcow.evm_address: (self._decode_cow_claim,),
        }
