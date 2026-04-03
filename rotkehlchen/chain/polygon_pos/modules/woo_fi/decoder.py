from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.woo_fi.decoder import WooFiStakingDecoder, WooVaultInfo
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class WooFiDecoder(WooFiStakingDecoder):

    def __init__(
            self,
            polygon_pos_inquirer: 'PolygonPOSInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=polygon_pos_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            earn_vaults=[WooVaultInfo(  # POL
                token=string_to_evm_address('0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270'),
                supercharger=string_to_evm_address('0x9DD5dD86b978f17628f01307A83347d9Ec9B0699'),
                withdraw_manager=string_to_evm_address('0x382A9b0bC5D29e96c3a0b81cE9c64d6C8F150Efb'),
            ), WooVaultInfo(  # ETH
                token=string_to_evm_address('0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619'),
                supercharger=string_to_evm_address('0xeDBB74dA05D58b22F07184BB79ED9124791799Ac'),
                withdraw_manager=string_to_evm_address('0x7f78213da92552D00Bd676466aB2ef8A9287Fd4C'),
            ), WooVaultInfo(  # USDC
                token=string_to_evm_address('0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359'),
                supercharger=string_to_evm_address('0x1109E03516eB25eAb2150D0b274B8D4F5F3cF549'),
                withdraw_manager=string_to_evm_address('0x3Fe2c827FF572B8fe03b7d16695c88F21448B3B9'),
            )],
            woo_token_address=string_to_evm_address('0x1B815d120B3eF02039Ee11dC2d33DE7aA4a8C603'),
            stake_v1_address=string_to_evm_address('0x9BCf8b0B62F220f3900e2dc42dEB85C3f79b405B'),
            stake_v2_address=string_to_evm_address('0xba91ffD8a2B9F68231eCA6aF51623B3433A89b13'),
        )
