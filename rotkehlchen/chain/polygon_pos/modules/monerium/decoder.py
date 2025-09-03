from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.monerium.decoder import MoneriumCommonDecoder
from rotkehlchen.chain.polygon_pos.modules.monerium.constants import POLYGON_MONERIUM_ADDRESSES

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class MoneriumDecoder(MoneriumCommonDecoder):

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
            monerium_token_addresses=POLYGON_MONERIUM_ADDRESSES,
        )

    def _v1_to_v2_migration_hashes(self) -> set[str]:
        return {
            '0xa5524ff7537a4ef263888d2fbcc9d0923fe970e4f359acb8117389e73a7169cf',
            '0xfae6ab7a5b077b3bb11a7387c1fa3448c3bd35d6c0b9c08e7879cfed4b1128cf',
            '0x53983babd143050c77941f5ed0a4ad09ebeb2d0e8dac571bee3ddc220234652d',
            '0xb13b6de3369fee54942a35add045278998ab2cc2ce504ac314d37d6b6dd02d60',
        }
