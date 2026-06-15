from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.balancer.v3.constants import (
    SWAP_TOPIC as BALANCER_V3_SWAP_TOPIC,
)
from rotkehlchen.chain.evm.decoding.oneinch.constants import CPT_ONEINCH_V6, ONEINCH_V6_ROUTER
from rotkehlchen.chain.evm.decoding.oneinch.decoder import OneinchCommonDecoder
from rotkehlchen.chain.evm.decoding.oneinch.v4.decoder import Oneinchv3n4DecoderBase
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

# OrderFilled(bytes32,uint256) of the limit order protocol v4 embedded in the v6 router.
ORDER_FILLED_TOPIC: Final = b'\xfe\xc315\x0f\xcex\xbae\x8e\x08*q\xda \xac\x9f\x8dy\x8a\x99\xb3\xc7\x96\x81\xc8D\x0c\xbf\xe7~\x07'  # noqa: E501


class Oneinchv6Decoder(Oneinchv3n4DecoderBase):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_address=ONEINCH_V6_ROUTER,
            counterparty=CPT_ONEINCH_V6,
            # The v6 router emits the OrderFilled log after the transfers, so it is paired
            # during decoding via addresses_to_decoders below. The topic is still registered
            # here so the post-decoding rule can recognize (and skip) the already-paired swap.
            limit_order_topics=[ORDER_FILLED_TOPIC],
        )
        # Balancer V3 is reachable through 1inch Fusion routing, so its swap log can be the
        # only pool-side signature emitted in an otherwise opaque v6 swap transaction.
        self.swapped_signatures.append(BALANCER_V3_SWAP_TOPIC)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return super().addresses_to_decoders() | {
            self.router_address: (self._decode_limit_order_swap,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return OneinchCommonDecoder.generate_counterparty_details(CPT_ONEINCH_V6)
