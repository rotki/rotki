import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.yearn.constants import (
    ARBITRUM_YEARN_PARTNER_TRACKER,
)
from rotkehlchen.chain.evm.decoding.yearn.decoder import YearnCommonDecoder
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.manager import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class YearnDecoder(YearnCommonDecoder):
    def __init__(
            self,
            arbitrum_one_inquirer: 'ArbitrumOneInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=arbitrum_one_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            yearn_partner_tracker=ARBITRUM_YEARN_PARTNER_TRACKER,
        )
