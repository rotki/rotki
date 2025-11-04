from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.morpho.decoder import MorphoCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.binance_sc.node_inquirer import BinanceSCInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class MorphoDecoder(MorphoCommonDecoder):

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
            bundlers={string_to_evm_address('0x16D40b9DF1497468195BFAfeb2718e486E15bF91')},  # Bundler3  # noqa: E501
            adapters={
                string_to_evm_address('0x87c93660ECe6E68C6492EabBbBdbaafA102ae3a3'),  # GeneralAdapter1  # noqa: E501
                string_to_evm_address('0xBb12B012Fa31f7FE418236cAf625713Edc852F82'),  # ParaswapAdapter  # noqa: E501
            },
        )
