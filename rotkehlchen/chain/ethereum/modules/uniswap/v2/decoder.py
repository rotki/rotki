from typing import TYPE_CHECKING, Callable, Optional

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.modules.uniswap.constants import CPT_UNISWAP_V2
from rotkehlchen.chain.ethereum.modules.uniswap.utils import decode_basic_uniswap_info
from rotkehlchen.chain.ethereum.modules.uniswap.v2.common import (
    UNISWAP_V2_ROUTER,
    decode_uniswap_v2_like_swap,
)
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import ActionItem
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.types import EvmTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

# https://www.4byte.directory/api/v1/event-signatures/?hex_signature=0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822  # noqa: E501
SWAP_SIGNATURE = b'\xd7\x8a\xd9_\xa4l\x99KeQ\xd0\xda\x85\xfc\'_\xe6\x13\xce7e\x7f\xb8\xd5\xe3\xd10\x84\x01Y\xd8"'  # noqa: E501


class Uniswapv2Decoder(DecoderInterface):

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
        )
        self.database = ethereum_inquirer.database
        self.ethereum_inquirer = ethereum_inquirer

    def _decode_basic_swap_info(
            self,
            tx_log: EvmTxReceiptLog,
            decoded_events: list[HistoryBaseEntry],
    ) -> None:
        """
        Decodes only basic swap info. Basic swap info includes trying to find approval, spend and
        receive events for this particular swap but doesn't include ensuring order of events if the
        swap was made by an aggregator.
        """
        # amount_in is the amount that enters the pool and amount_out the one
        # that leaves the pool
        amount_in_token_0, amount_in_token_1 = hex_or_bytes_to_int(tx_log.data[0:32]), hex_or_bytes_to_int(tx_log.data[32:64])  # noqa: E501
        amount_out_token_0, amount_out_token_1 = hex_or_bytes_to_int(tx_log.data[64:96]), hex_or_bytes_to_int(tx_log.data[96:128])  # noqa: E501
        amount_in, amount_out = amount_in_token_0, amount_out_token_0
        if amount_in == ZERO:
            amount_in = amount_in_token_1
        if amount_out == ZERO:
            amount_out = amount_out_token_1

        decode_basic_uniswap_info(
            amount_sent=amount_in,
            amount_received=amount_out,
            decoded_events=decoded_events,
            counterparty=CPT_UNISWAP_V2,
            notify_user=self.notify_user,
        )

    def _maybe_decode_v2_swap(  # pylint: disable=no-self-use
            self,
            token: Optional[EvmToken],  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list[HistoryBaseEntry],
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> None:
        if tx_log.topics[0] == SWAP_SIGNATURE:
            if transaction.to_address == UNISWAP_V2_ROUTER:
                # If uniswap v2 router is used, then we can decode an entire swap.
                # Uniswap v2 router is a simple router that always has a single spend and a single
                # receive event.
                decode_uniswap_v2_like_swap(
                    tx_log=tx_log,
                    decoded_events=decoded_events,
                    transaction=transaction,
                    counterparty=CPT_UNISWAP_V2,
                    database=self.database,
                    ethereum_inquirer=self.ethereum_inquirer,
                    notify_user=self.notify_user,
                )
            else:
                # Else some aggregator (potentially complex) is used, so we decode only basic info
                # and other properties should be decoded by the aggregator decoding methods later.
                self._decode_basic_swap_info(tx_log=tx_log, decoded_events=decoded_events)

    # -- DecoderInterface methods

    def decoding_rules(self) -> list[Callable]:
        return [
            self._maybe_decode_v2_swap,
        ]

    def counterparties(self) -> list[str]:
        return [CPT_UNISWAP_V2]
