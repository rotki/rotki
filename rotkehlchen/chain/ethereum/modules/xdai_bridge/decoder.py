from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.xdai_bridge.decoder import XdaiBridgeCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.types import ChainID

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

BRIDGE_ADDRESS = string_to_evm_address('0x4aa42145Aa6Ebf72e164C9bBC74fbD3788045016')
BRIDGE_DAI = b'\x1dI\x1aB}\x1f\x8c\xc0\xd4GIo0\x0f\xac9\xf70a"H\x1d\x8ef4Q\xeb&\x82t\x14k'
WITHDRAW_DAI = b'J\xb7\xd5\x813m\x92\xed\xbe\xa2&6\xa6\x13\xe8\xe7l\x99\xac\x7f\x91\x13|\x15#\xdb8\xdb\xfb;\xf3)'  # noqa: E501


class XdaiBridgeDecoder(XdaiBridgeCommonDecoder):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            deposit_topic=BRIDGE_DAI,
            withdrawal_topic=WITHDRAW_DAI,
            bridge_address=BRIDGE_ADDRESS,
            bridged_asset=A_DAI,
            source_chain=ChainID.ETHEREUM,
            target_chain=ChainID.GNOSIS,
        )
