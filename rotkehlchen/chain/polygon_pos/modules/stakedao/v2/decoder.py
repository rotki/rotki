from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.stakedao.v2.decoder import Stakedaov2CommonDecoder

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class Stakedaov2Decoder(Stakedaov2CommonDecoder):

    def __init__(
            self,
            polygon_pos_inquirer: 'PolygonPOSInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ):
        super().__init__(
            evm_inquirer=polygon_pos_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            accountant_address=None,
            reward_token_address=None,
        )
