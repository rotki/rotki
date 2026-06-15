from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.modules.oneinch.constants import CPT_ONEINCH_V5
from rotkehlchen.chain.evm.decoding.oneinch.decoder import OneinchCommonDecoder
from rotkehlchen.chain.evm.decoding.oneinch.v4.decoder import Oneinchv3n4DecoderBase
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

ONEINCH_V5_ROUTER = string_to_evm_address('0x1111111254EEB25477B68fb85Ed929f73A960582')
# OrderFilled(address,bytes32,uint256) of the limit order protocol v3 embedded in the v5 router.
# Emitted when a 1inch limit order / Fusion order is settled through the v5 router.
ORDER_FILLED_TOPIC: Final = b'\xb9\xed\x02C\xfd\xf0\x0f\x05E\xc6:\n\xf8\x85\x0c\t\r\x86\xbbFh+\xae\xc4\xbf<Ih\x14\xfeO\x02'  # noqa: E501


class Oneinchv5Decoder(Oneinchv3n4DecoderBase):

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
            router_address=ONEINCH_V5_ROUTER,
            counterparty=CPT_ONEINCH_V5,
            limit_order_topics=[ORDER_FILLED_TOPIC],
        )

    # -- DecoderInterface methods

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return OneinchCommonDecoder.generate_counterparty_details(CPT_ONEINCH_V5)
