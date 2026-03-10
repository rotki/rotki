from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.crosscurve.constants import UNIFIED_ROUTER_V2
from rotkehlchen.chain.evm.decoding.crosscurve.decoder import CrossCurveCommonDecoder

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class CrosscurveDecoder(CrossCurveCommonDecoder):
    def __init__(
            self,
            evm_inquirer: 'PolygonPOSInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_addresses=(UNIFIED_ROUTER_V2,),
        )
