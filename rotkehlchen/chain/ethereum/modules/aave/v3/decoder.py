from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.aave.v3.constants import POOL_ADDRESS
from rotkehlchen.chain.evm.decoding.aave.v3.decoder import Aavev3LikeCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class Aavev3Decoder(Aavev3LikeCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            pool_addresses=(
                POOL_ADDRESS,
                string_to_evm_address('0x4e033931ad43597d96D6bcc25c280717730B58B1'),  # lido pool
                string_to_evm_address('0x0AA97c284e98396202b6A04024F5E2c65026F3c0'),  # etherfi
            ),
            native_gateways=(
                string_to_evm_address('0x893411580e590D62dDBca8a703d61Cc4A8c7b2b9'),
                string_to_evm_address('0xA434D495249abE33E031Fe71a969B81f3c07950D'),
                string_to_evm_address('0xd01607c3C5eCABa394D8be377a08590149325722'),
            ),
            treasury=string_to_evm_address('0x464C71f6c2F760DdA6093dCB91C24c39e5d6e18c'),
            incentives=string_to_evm_address('0x8164Cc65827dcFe994AB23944CBC90e0aa80bFcb'),
            collateral_swap_address=string_to_evm_address('0xADC0A53095A0af87F3aa29FE0715B5c28016364e'),
        )
