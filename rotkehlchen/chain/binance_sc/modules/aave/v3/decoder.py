from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.aave.v3.decoder import Aavev3LikeCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.binance_sc.node_inquirer import BinanceSCInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class Aavev3Decoder(Aavev3LikeCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'BinanceSCInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            pool_addresses=(string_to_evm_address('0x6807dc923806fE8Fd134338EABCA509979a7e0cB'),),
            native_gateways=(string_to_evm_address('0xe63eAf6DAb1045689BD3a332bC596FfcF54A5C88'),),
            treasury=string_to_evm_address('0x25Ec457d1778b0E5316e7f38f3c22baF413F1A8C'),
            incentives=string_to_evm_address('0xC206C2764A9dBF27d599613b8F9A63ACd1160ab4'),
            collateral_swap_address=string_to_evm_address('0x33E0b3fc976DC9C516926BA48CfC0A9E10a2aAA5'),
        )
