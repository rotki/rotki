from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.woo_fi.decoder import WooFiStakingDecoder, WooVaultInfo
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class WooFiDecoder(WooFiStakingDecoder):

    def __init__(
            self,
            base_inquirer: 'BaseInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=base_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            earn_vaults=[WooVaultInfo(  # USDC
                token=string_to_evm_address('0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),
                supercharger=string_to_evm_address('0x44dF096D2600C6a6db77899dB3DE3AeCff746cb8'),
                withdraw_manager=string_to_evm_address('0xa1bb8a8ED84A37a8c93a10Df5153E612f58e34E5'),
            ), WooVaultInfo(  # WETH/ETH
                token=string_to_evm_address('0x4200000000000000000000000000000000000006'),
                supercharger=string_to_evm_address('0xb772122C4a37fe1754B46AB1799b909351e8Cb43'),
                withdraw_manager=string_to_evm_address('0xe61Acb121a2B538dF495A85C4E50dD8581de4ed0'),
            ), WooVaultInfo(  # cbBTC
                token=string_to_evm_address('0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf'),
                supercharger=string_to_evm_address('0x8C603050D7a913b6f63836e07ebF385a4A5736E7'),
                withdraw_manager=string_to_evm_address('0xEc054126922a9a1918435c9072c32f1B60cB2B90'),
            )],
            woo_token_address=string_to_evm_address('0xF3df0A31ec5EA438150987805e841F960b9471b6'),
        )
