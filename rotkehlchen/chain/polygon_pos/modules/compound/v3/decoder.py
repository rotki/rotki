import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.compound.v3.decoder import Compoundv3CommonDecoder
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .constants import COMPOUND_REWARDS_ADDRESS

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Compoundv3Decoder(Compoundv3CommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'PolygonPOSInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            rewards_address=COMPOUND_REWARDS_ADDRESS,
        )
