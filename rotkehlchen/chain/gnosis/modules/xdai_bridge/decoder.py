from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.xdai_bridge.decoder import XdaiBridgeCommonDecoder
from rotkehlchen.constants.assets import A_XDAI
from rotkehlchen.types import ChainID

from .constants import BRIDGE_ADDRESS

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
    from rotkehlchen.user_messages import MessagesAggregator


BRIDGE_XDAI = b'\x12vP\xbc\xfb\x0b\xa0\x17@\x1a\xbeI1E:@Q@\xa8\xfd6\xfe\xceg\xba\xe2\xdb\x17M?\xddc'  # noqa: E501
AFFIRMATION_COMPLETED = b'o\xc1\x15\xa8\x03\xb8p1\x17\xd9\xa3\x95lZ\x15@\x1c\xb4$\x01\xf9\x160\xf0\x15\xebk\x04?\xa7bS'  # noqa: E501


class XdaiBridgeDecoder(XdaiBridgeCommonDecoder):

    def __init__(
            self,
            gnosis_inquirer: 'GnosisInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=gnosis_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            deposit_topics=(BRIDGE_XDAI,),
            withdrawal_topic=AFFIRMATION_COMPLETED,
            bridge_address=BRIDGE_ADDRESS,  # TODO: There may be more bridge addresses judging by the way the logs and contract are made  # noqa: E501
            bridged_asset=A_XDAI,
            source_chain=ChainID.GNOSIS,
            target_chain=ChainID.ETHEREUM,
        )
