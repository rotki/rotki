import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.uniswap.v3.constants import SWAP_SIGNATURE
from rotkehlchen.chain.evm.decoding.uniswap.v3.utils import (
    decode_uniswap_v3_like_router_swap,
)
from rotkehlchen.errors.misc import BlockchainQueryError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address

from .constants import (
    CPT_KITTENSWAP,
    KITTENSWAP_FACTORY,
    KITTENSWAP_FACTORY_ABI,
    KITTENSWAP_POOL_ABI,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.chain.hyperliquid.node_inquirer import HyperliquidInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class KittenswapDecoder(EvmDecoderInterface):

    def __init__(
            self,
            evm_inquirer: HyperliquidInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.valid_pools: set[ChecksumEvmAddress] = set()
        self.invalid_pools: set[ChecksumEvmAddress] = set()

    def _is_valid_pool(
            self,
            pool_address: ChecksumEvmAddress,
            block_number: int,
    ) -> bool:
        """Return whether the pool is registered by the KittenSwap factory."""
        if pool_address in self.valid_pools:
            return True
        if pool_address in self.invalid_pools:
            return False

        try:
            if deserialize_evm_address(self.node_inquirer.call_contract(
                contract_address=pool_address,
                abi=KITTENSWAP_POOL_ABI,
                method_name='factory',
                block_identifier=block_number,
            )) != KITTENSWAP_FACTORY:
                self.invalid_pools.add(pool_address)
                return False

            token0_address = deserialize_evm_address(self.node_inquirer.call_contract(
                contract_address=pool_address,
                abi=KITTENSWAP_POOL_ABI,
                method_name='token0',
                block_identifier=block_number,
            ))
            token1_address = deserialize_evm_address(self.node_inquirer.call_contract(
                contract_address=pool_address,
                abi=KITTENSWAP_POOL_ABI,
                method_name='token1',
                block_identifier=block_number,
            ))
            registered_pool = deserialize_evm_address(self.node_inquirer.call_contract(
                contract_address=KITTENSWAP_FACTORY,
                abi=KITTENSWAP_FACTORY_ABI,
                method_name='poolByPair',
                arguments=[token0_address, token1_address],
                block_identifier=block_number,
            ))
        except (RemoteError, BlockchainQueryError) as e:
            log.debug('Failed to verify potential KittenSwap pool %s: %s', pool_address, e)
            return False
        except DeserializationError as e:
            log.debug('KittenSwap pool %s returned invalid contract data: %s', pool_address, e)
            self.invalid_pools.add(pool_address)
            return False

        if registered_pool != pool_address:
            self.invalid_pools.add(pool_address)
            return False

        self.valid_pools.add(pool_address)
        return True

    def _decode_swap(self, context: DecoderContext) -> EvmDecodingOutput:
        if (
            context.tx_log.topics[0] != SWAP_SIGNATURE or
            self._is_valid_pool(
                pool_address=context.tx_log.address,
                block_number=context.transaction.block_number,
            ) is False
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        # Generic decoding rules only propagate outputs which create events/actions or request
        # swap processing. The latter also ensures the post-decoded endpoints become swap events.
        return EvmDecodingOutput(
            matched_counterparty=CPT_KITTENSWAP,
            process_swaps=True,
        )

    def _maybe_decode_swap(
            self,
            token: EvmToken | None,  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            action_items: list[ActionItem],
            all_logs: list[EvmTxReceiptLog],
    ) -> EvmDecodingOutput:
        return self._decode_swap(DecoderContext(
            tx_log=tx_log,
            transaction=transaction,
            decoded_events=decoded_events,
            action_items=action_items,
            all_logs=all_logs,
        ))

    def decoding_rules(self) -> list[Callable]:
        """Pools are dynamic, so validate V3 Swap emitters against the factory on first sight."""
        return [self._maybe_decode_swap]

    @staticmethod
    def _swap_post_decoding(
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> list[EvmEvent]:
        return decode_uniswap_v3_like_router_swap(
            transaction=transaction,
            decoded_events=decoded_events,
            counterparty=CPT_KITTENSWAP,
            spend_notes='Swap {amount} {symbol} in KittenSwap',
            receive_notes='Receive {amount} {symbol} as the result of a swap in KittenSwap',
        )

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_KITTENSWAP: [(0, self._swap_post_decoding)]}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_KITTENSWAP,
            label='KittenSwap',
            image='kittenswap.png',
        ),)
