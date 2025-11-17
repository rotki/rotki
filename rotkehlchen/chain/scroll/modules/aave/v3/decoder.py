from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.aave.v3.decoder import Aavev3LikeCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.scroll.node_inquirer import ScrollInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class Aavev3Decoder(Aavev3LikeCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'ScrollInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            pool_addresses=(string_to_evm_address('0x11fCfe756c05AD438e312a7fd934381537D3cFfe'),),
            native_gateways=(
                string_to_evm_address('0x31A239f3e39c5D8BA6B201bA81ed584492Ae960F'),
                string_to_evm_address('0xFF75A4B698E3Ec95E608ac0f22A03B8368E05F5D'),
                string_to_evm_address('0xE79Ca44408Dae5a57eA2a9594532f1E84d2edAa4'),
            ),
            treasury=string_to_evm_address('0x90eB541e1a431D8a30ED85A77675D1F001128cb5'),
            incentives=string_to_evm_address('0xa3f3100C4f1D0624DB9DB97b40C13885Ce297799'),
        )
