from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.modules.monerium.constants import ETHEREUM_MONERIUM_ADDRESSES
from rotkehlchen.chain.evm.decoding.monerium.decoder import MoneriumCommonDecoder

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class MoneriumDecoder(MoneriumCommonDecoder):

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
            monerium_token_addresses=ETHEREUM_MONERIUM_ADDRESSES,
        )

    def _v1_to_v2_migration_hashes(self) -> set[str]:
        """Hashes of the transactions minting v2 tokens by Monerium for the v1 to v2 migration
        Events in those transactions shouldn't be decoded as mints.
        Present in gnosis, polygon and ethereum.
        """
        return {
            '0xef41ba0da2e98f6911e9257ea8bd21260097f71e70d8378113ff8c8c3c6d7833',
            '0x69e046e34fb5c6e10dab90ec5da692c1d1ccc9d843fd4c6eba17d61686cf45f1',
        }
