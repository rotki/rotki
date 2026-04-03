from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.woo_fi.decoder import WooFiStakingDecoder, WooVaultInfo
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class WooFiDecoder(WooFiStakingDecoder):

    def __init__(
            self,
            arbitrum_one_inquirer: 'ArbitrumOneInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=arbitrum_one_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            earn_vaults=[WooVaultInfo(  # USDC
                token=string_to_evm_address('0xaf88d065e77c8cC2239327C5EDb3A432268e5831'),
                supercharger=string_to_evm_address('0xA780432f495E5C6851fd7903FE49ad77C952F7D8'),
                withdraw_manager=string_to_evm_address('0xE76c97897A9c3f8aAAfC3Fe86457Fe460553D3FE'),
            ), WooVaultInfo(  # WBTC
                token=string_to_evm_address('0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f'),
                supercharger=string_to_evm_address('0xd2fdaB19b94B59C5F0E75Dd9813365Df815b56B1'),
                withdraw_manager=string_to_evm_address('0xD05b953cFD75426711a904F76eb3241bad5D03ac'),
            ), WooVaultInfo(  # WETH/ETH
                token=string_to_evm_address('0x82aF49447D8a07e3bd95BD0d56f35241523fBab1'),
                supercharger=string_to_evm_address('0xba452bCc4BC52AF2fe1190e7e1dBE267ad1C2d08'),
                withdraw_manager=string_to_evm_address('0xE77ADf3936F70a2Ed44f26CeD01d26c1430EAd6a'),
            ), WooVaultInfo(  # ARB
                token=string_to_evm_address('0x912CE59144191C1204E64559FE8253a0e49E6548'),
                supercharger=string_to_evm_address('0x7f3F2A499c00c2D7018300F99A232896fD295Bb1'),
                withdraw_manager=string_to_evm_address('0xBFe3d22B223909A06469854E7Af374ab449F09AC'),
            ), WooVaultInfo(  # USDC.e
                token=string_to_evm_address('0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8'),
                supercharger=string_to_evm_address('0x5a6B073E090388C909b9F3bf9D9323be908cAD62'),
                withdraw_manager=string_to_evm_address('0x7dE3FCe3De3CdC34595eEd74773CD47b84bCa340'),
            )],
            woo_token_address=string_to_evm_address('0xcAFcD85D8ca7Ad1e1C6F82F651fA15E33AEfD07b'),
            stake_v1_address=string_to_evm_address('0x9321785D257b3f0eF7Ff75436a87141C683DC99d'),
            stake_v2_address=string_to_evm_address('0x2CFa72E7f58dc82B990529450Ffa83791db7d8e2'),
        )
