from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.woo_fi.decoder import WooFiStakingDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class WooFiDecoder(WooFiStakingDecoder):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            earn_vaults=[],  # There are no WOOFi earn (supercharger) vaults deployed on ethereum.
            woo_token_address=string_to_evm_address('0x4691937a7508860F876c9c0a2a617E7d9E945D4B'),
            stake_v2_address=string_to_evm_address('0xba91ffD8a2B9F68231eCA6aF51623B3433A89b13'),
        )
