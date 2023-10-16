from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.xdai_bridge.decoder import XdaiBridgeCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_XDAI
from rotkehlchen.types import ChainID

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
    from rotkehlchen.user_messages import MessagesAggregator


BRIDGE_ADDRESS = string_to_evm_address('0x7301CFA0e1756B71869E93d4e4Dca5c7d0eb0AA6')
BRIDGE_XDAI = b'\x12vP\xbc\xfb\x0b\xa0\x17@\x1a\xbeI1E:@Q@\xa8\xfd6\xfe\xceg\xba\xe2\xdb\x17M?\xddc'  # noqa: E501


class XdaiBridgeDecoder(XdaiBridgeCommonDecoder):

    def __init__(
            self,
            gnosis_inquirer: 'GnosisInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=gnosis_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            deposit_topic=BRIDGE_XDAI,
            withdrawal_topic=None,  # TODO: decode bridge withdrawal, currently unsupported by gnosisscan https://github.com/orgs/rotki/projects/11?pane=issue&itemId=41923920  # noqa: E501
            bridge_address=BRIDGE_ADDRESS,
            bridged_asset=A_XDAI,
            source_chain=ChainID.GNOSIS,
            target_chain=ChainID.ETHEREUM,
        )
