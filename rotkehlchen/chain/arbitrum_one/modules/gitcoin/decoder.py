import logging
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.decoding.gitcoin.decoder import GitcoinOldCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GitcoinDecoder(GitcoinOldCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        GitcoinOldCommonDecoder.__init__(
            self,
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            matching_contracts2=[
                (string_to_evm_address('0xeD67d6682DC88E06c66e188027cA883455AfdADa'), 'grants 14 round', EvmToken('eip155:42161/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1')),  # not sure which subround this was #  noqa: E501
            ],
        )
