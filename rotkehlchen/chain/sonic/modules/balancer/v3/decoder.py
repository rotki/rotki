from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.balancer.constants import (
    BEETS_LABEL,
    CPT_BEETS_SWAP_V3,
    CPT_BEETS_V3,
)
from rotkehlchen.chain.evm.decoding.balancer.v3.decoder import Balancerv3CommonDecoder

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.sonic.node_inquirer import SonicInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class Balancerv3Decoder(Balancerv3CommonDecoder):

    def __init__(
            self,
            evm_inquirer: SonicInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            counterparty=CPT_BEETS_V3,
            swap_counterparty=CPT_BEETS_SWAP_V3,
            label=BEETS_LABEL,
            image='beets.svg',
        )
