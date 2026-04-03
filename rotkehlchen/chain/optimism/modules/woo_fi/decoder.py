from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.woo_fi.decoder import WooFiStakingDecoder, WooVaultInfo
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class WooFiDecoder(WooFiStakingDecoder):

    def __init__(
            self,
            optimism_inquirer: 'OptimismInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=optimism_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            earn_vaults=[WooVaultInfo(  # WETH/ETH
                token=string_to_evm_address('0x4200000000000000000000000000000000000006'),
                supercharger=string_to_evm_address('0xB54e1d90d845d888d39dcaCBd54a3EEc0d8853B2'),
                withdraw_manager=string_to_evm_address('0x91741863A48f0B29fC0B6D10b3cdE2122feB58f7'),
            ), WooVaultInfo(  # OP
                token=string_to_evm_address('0x4200000000000000000000000000000000000042'),
                supercharger=string_to_evm_address('0xcA7184eA1cb4cF04d49Bf219c49a39231299dA26'),
                withdraw_manager=string_to_evm_address('0x0FAd8f10746171C0616cE4B7B4E2e9439a9a02E2'),
            ), WooVaultInfo(  # USDC
                token=string_to_evm_address('0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85'),
                supercharger=string_to_evm_address('0x18aa88bb25b8f15FDbE329f789dD000bf679753E'),
                withdraw_manager=string_to_evm_address('0x2500AD59b46fF4B96f8e1EaC3fE1f78eAF955777'),
            )],
            woo_token_address=string_to_evm_address('0x871f2F2ff935FD1eD867842FF2a7bfD051A5E527'),
            stake_v2_address=string_to_evm_address('0xba91ffD8a2B9F68231eCA6aF51623B3433A89b13'),
        )
