from typing import TYPE_CHECKING, Callable, List, Optional

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.modules.sushiswap.constants import CPT_SUSHISWAP_V2
from rotkehlchen.chain.ethereum.modules.uniswap.v2.common import decode_uniswap_v2_like_swap
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.types import EvmTransaction

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.user_messages import MessagesAggregator

# https://www.4byte.directory/api/v1/event-signatures/?hex_signature=0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822  # noqa: E501
SWAP_SIGNATURE = b'\xd7\x8a\xd9_\xa4l\x99KeQ\xd0\xda\x85\xfc\'_\xe6\x13\xce7e\x7f\xb8\xd5\xe3\xd10\x84\x01Y\xd8"'  # noqa: E501


class SushiswapDecoder(DecoderInterface):

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            ethereum_manager=ethereum_manager,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.database = ethereum_manager.database
        self.ethereum_manager = ethereum_manager

    def _maybe_decode_v2_swap(  # pylint: disable=no-self-use
            self,
            token: Optional[EvmToken],  # pylint: disable=unused-argument
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: List[HistoryBaseEntry],
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> None:
        if tx_log.topics[0] == SWAP_SIGNATURE:
            decode_uniswap_v2_like_swap(
                tx_log=tx_log,
                decoded_events=decoded_events,
                transaction=transaction,
                counterparty=CPT_SUSHISWAP_V2,
                database=self.database,
                ethereum_manager=self.ethereum_manager,
                notify_user=self.notify_user,
            )

    # -- DecoderInterface methods

    def decoding_rules(self) -> List[Callable]:
        return [
            self._maybe_decode_v2_swap,
        ]

    def counterparties(self) -> List[str]:
        return [CPT_SUSHISWAP_V2]
