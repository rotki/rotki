import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.modules.uniswap.v2.constants import SWAP_SIGNATURE
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import ActionItem
from rotkehlchen.chain.evm.decoding.uniswap_v2_like.common import (
    compute_uniswap_v2_like_pool_address_with_unpacked_addresses,
    decode_uniswap_like_deposit_and_withdrawals,
    decode_uniswap_v2_like_swap,
)
from rotkehlchen.chain.evm.decoding.uniswap_v2_like.constants import (
    BURN_SIGNATURES,
    MINT_SIGNATURE,
)
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class UniswapV2LikeDecoder(DecoderInterface):
    weth_asset: EvmToken | None = None

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            counterparty_addresses: list[ChecksumEvmAddress],
            pool_address_setup: dict[ChecksumEvmAddress, str],
    ) -> None:
        super().__init__(evm_inquirer, base_tools, msg_aggregator)
        self.counterparty_addresses = counterparty_addresses
        self.pool_address_setup = pool_address_setup

    def _post_decode_events(
            self,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            all_logs: list[EvmTxReceiptLog],
    ) -> list['EvmEvent']:
        for tx_log in all_logs:
            self._maybe_decode_v2_swap(
                tx_log=tx_log,
                transaction=transaction,
                decoded_events=decoded_events,
                token=None,
                action_items=[],
                all_logs=all_logs,
            )
            self._maybe_decode_liquidity_addition_and_removal(
                tx_log=tx_log,
                transaction=transaction,
                decoded_events=decoded_events,
                token=None,
                action_items=[],
                all_logs=all_logs,
            )
        return decoded_events

    def _maybe_decode_v2_swap(
            self,
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            token: EvmToken | None,  # pylint: disable=unused-argument
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> None:
        """Decodes the swap if the event log matches the swap signature.
        Does not return anything because it modifies the decoded_events list
        """
        if tx_log.topics[0] != SWAP_SIGNATURE:
            return

        decode_uniswap_v2_like_swap(
            tx_log=tx_log,
            transaction=transaction,
            decoded_events=decoded_events,
            counterparty=self.counterparties()[0].identifier,
            database=self.base.database,
            evm_inquirer=self.evm_inquirer,
            notify_user=self.notify_user,
            counterparty_addresses=self.counterparty_addresses,
        )

    def _maybe_decode_liquidity_addition_and_removal(
            self,
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            token: EvmToken | None,  # pylint: disable=unused-argument
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> None:
        if tx_log.topics[0] == MINT_SIGNATURE:
            event_action_type: Literal['addition', 'removal'] = 'addition'
        elif tx_log.topics[0] in BURN_SIGNATURES:
            event_action_type = 'removal'
        else:
            return

        if self.weth_asset is None:
            log.error('UniswapV2LikeDecoder: weth_asset has not been set by the subclass')
            return

        # Decode pool events for each factory
        for factory_address, init_code_hash in self.pool_address_setup.items():
            decode_uniswap_like_deposit_and_withdrawals(
                tx_log=tx_log,
                decoded_events=decoded_events,
                all_logs=all_logs,
                event_action_type=event_action_type,
                counterparty=self.counterparties()[0].identifier,
                evm_inquirer=self.evm_inquirer,
                database=self.evm_inquirer.database,
                factory_address=factory_address,
                init_code_hash=init_code_hash,
                tx_hash=transaction.tx_hash,
                weth_asset=self.weth_asset,
                compute_pool_address=compute_uniswap_v2_like_pool_address_with_unpacked_addresses,
            )

    # -- DecoderInterface methods

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        """The swap is decoded in the post decoding rules because ERC20 transfers could occur before the swap event"""  # noqa: E501
        return {self.counterparties()[0].identifier: [(0, self._post_decode_events)]}
