from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.woo_fi.decoder import WooFiStakingDecoder, WooVaultInfo
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.binance_sc.node_inquirer import BinanceSCInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class WooFiDecoder(WooFiStakingDecoder):

    def __init__(
            self,
            binance_sc_inquirer: 'BinanceSCInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=binance_sc_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            earn_vaults=[WooVaultInfo(  # BNB
                token=string_to_evm_address('0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'),
                supercharger=string_to_evm_address('0x7eb8D4CcFDBD9dF8d3520E9C5b5edf6a5Cbe4CaD'),
                withdraw_manager=string_to_evm_address('0x2698946AD5988759fa29093e9aF99eeA12a31bb4'),
            ), WooVaultInfo(  # USDT
                token=string_to_evm_address('0x55d398326f99059fF775485246999027B3197955'),
                supercharger=string_to_evm_address('0x5CB9ba4a6f05c4125D61172E1b2C1DBe3afb3158'),
                withdraw_manager=string_to_evm_address('0x3cBB7F9a4e1E8a8430f1d400DF269B80B6872DeB'),
            )],
            woo_token_address=string_to_evm_address('0x4691937a7508860F876c9c0a2a617E7d9E945D4B'),
            stake_v1_address=string_to_evm_address('0x2AEab1a338bCB1758f71BD5aF40637cEE2085076'),
            stake_v2_address=string_to_evm_address('0xba91ffD8a2B9F68231eCA6aF51623B3433A89b13'),
        )
