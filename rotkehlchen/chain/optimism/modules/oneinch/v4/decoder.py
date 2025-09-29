from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.modules.oneinch.constants import CPT_ONEINCH_V4
from rotkehlchen.chain.evm.decoding.oneinch.v4.decoder import Oneinchv3n4DecoderBase
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


ONEINCH_V4_ROUTER_OP = string_to_evm_address('0x1111111254760F7ab3F16433eea9304126DCd199')


class Oneinchv4Decoder(Oneinchv3n4DecoderBase):

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
            router_address=ONEINCH_V4_ROUTER_OP,
            counterparty=CPT_ONEINCH_V4,
        )
