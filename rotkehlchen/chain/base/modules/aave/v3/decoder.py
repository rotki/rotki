from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.aave.v3.decoder import Aavev3LikeCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class Aavev3Decoder(Aavev3LikeCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'BaseInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            pool_addresses=(string_to_evm_address('0xA238Dd80C259a72e81d7e4664a9801593F98d1c5'),),
            native_gateways=(
                string_to_evm_address('0x729b3EA8C005AbC58c9150fb57Ec161296F06766'),
                string_to_evm_address('0x8be473dCfA93132658821E67CbEB684ec8Ea2E74'),
            ),
            treasury=string_to_evm_address('0xBA9424d650A4F5c80a0dA641254d1AcCE2A37057'),
            incentives=string_to_evm_address('0xf9cc4F0D883F1a1eb2c253bdb46c254Ca51E1F44'),
            collateral_swap_address=string_to_evm_address('0x2E549104c516b8657A7D888494DfbAbD7C70b464'),
        )
