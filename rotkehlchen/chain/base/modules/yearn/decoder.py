import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.yearn.constants import BASE_YEARN_PARTNER_TRACKER
from rotkehlchen.chain.evm.decoding.yearn.decoder import YearnCommonDecoder
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.base.manager import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class YearnDecoder(YearnCommonDecoder):
    def __init__(
            self,
            base_inquirer: 'BaseInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=base_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            yearn_partner_tracker=BASE_YEARN_PARTNER_TRACKER,
        )
