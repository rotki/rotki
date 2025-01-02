import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.yearn.decoder import YearnCommonDecoder
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.polygon_pos.manager import PolygonPOSInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class YearnDecoder(YearnCommonDecoder):
    def __init__(
            self,
            polygon_pos_enquirer: 'PolygonPOSInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=polygon_pos_enquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
