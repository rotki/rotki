import logging
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.decoding.clrfund.decoder import ClrfundCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ClrfundDecoder(ClrfundCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',  # pylint: disable=unused-argument
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            rounds_data=[
                (string_to_evm_address('0xeD67d6682DC88E06c66e188027cA883455AfdADa'), string_to_evm_address('0xD2020926C0f1f8990DE806eBbAd510fa4b9b6f45'), 'Ethstaker round', EvmToken('eip155:42161/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1')),  # noqa: E501
                (string_to_evm_address('0x4A2d90844EB9C815eF10dB0371726F0ceb2848B0'), string_to_evm_address('0x998b330B1424e343b18D83169C19bca4DE39153F'), 'ETHColombia round', EvmToken('eip155:42161/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1')),  # noqa: E501
                (string_to_evm_address('0x806F08B7DD31fE0267e8c70C4bF8C4BfbBddE760'), string_to_evm_address('0xdDd296E5865813C37d41Ceb13bF21E7F93F46a89'), 'Round 9', EvmToken('eip155:42161/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1')),  # noqa: E501
            ],
        )
