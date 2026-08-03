import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.uniswap.utils import (
    decode_uniswap_v3_like_position_create_or_exit,
)
from rotkehlchen.chain.evm.decoding.uniswap.v3.constants import (
    COLLECT_LIQUIDITY_SIGNATURE,
    DECREASE_LIQUIDITY_SIGNATURE,
    INCREASE_LIQUIDITY_SIGNATURE,
)
from rotkehlchen.chain.evm.decoding.uniswap.v3.utils import (
    decode_uniswap_v3_like_deposit_or_withdrawal,
    decode_uniswap_v3_like_router_swap,
)
from rotkehlchen.errors.misc import BlockchainQueryError, RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    CPT_PROJECT_X,
    PROJECT_X_NFT_MANAGER,
    PROJECT_X_NFT_MANAGER_ABI,
    PROJECT_X_SWAP_ROUTER,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.chain.hyperliquid.node_inquirer import HyperliquidInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ProjectXDecoder(EvmDecoderInterface):

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

    @staticmethod
    def _fee_collection_count(all_logs: list[EvmTxReceiptLog]) -> int:
        collect_count = 0
        for tx_log in all_logs:
            if tx_log.address != PROJECT_X_NFT_MANAGER or len(tx_log.topics) == 0:
                continue

            if tx_log.topics[0] == DECREASE_LIQUIDITY_SIGNATURE:
                return 0
            if tx_log.topics[0] == COLLECT_LIQUIDITY_SIGNATURE:
                collect_count += 1

        return collect_count

    def _get_transfer_token_data(
            self,
            all_logs: list[EvmTxReceiptLog],
            amounts: tuple[int, int],
            is_deposit: bool,
    ) -> tuple[tuple[ChecksumEvmAddress, int], tuple[ChecksumEvmAddress, int]] | None:
        """Infer position tokens and actual amounts from tracked-address transfers."""
        token_data = []
        used_addresses = set()
        tracked_address_topic = 1 if is_deposit else 2
        for amount in amounts:
            best_match = None
            for tx_log in all_logs:
                if (
                        len(tx_log.topics) != 3 or
                        tx_log.topics[0] != ERC20_OR_ERC721_TRANSFER or
                        tx_log.address in used_addresses or
                        not self.base.is_tracked(bytes_to_address(
                            tx_log.topics[tracked_address_topic],
                        ))
                ):
                    continue

                raw_amount = int.from_bytes(tx_log.data)
                if (
                        abs(raw_amount - amount) <= 3 and
                        (best_match is None or abs(raw_amount - amount) < best_match[2])
                ):
                    best_match = tx_log.address, raw_amount, abs(raw_amount - amount)

            if best_match is None:
                return None

            token_data.append((best_match[0], best_match[1]))
            used_addresses.add(best_match[0])

        return token_data[0], token_data[1]

    def _decode_liquidity(self, context: DecoderContext) -> EvmDecodingOutput:
        is_fee_collection = False
        if context.tx_log.topics[0] == INCREASE_LIQUIDITY_SIGNATURE:
            is_deposit = True
            amount0_raw = int.from_bytes(context.tx_log.data[32:64])
            amount1_raw = int.from_bytes(context.tx_log.data[64:96])
        elif context.tx_log.topics[0] == COLLECT_LIQUIDITY_SIGNATURE:
            if (fee_collection_count := self._fee_collection_count(context.all_logs)) > 1:
                return EvmDecodingOutput(matched_counterparty=CPT_PROJECT_X)

            is_deposit = False
            is_fee_collection = fee_collection_count == 1
            amount0_raw = int.from_bytes(context.tx_log.data[32:64])
            amount1_raw = int.from_bytes(context.tx_log.data[64:96])
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        position_id = int.from_bytes(context.tx_log.topics[1])
        if (token_data := self._get_transfer_token_data(
            all_logs=context.all_logs,
            amounts=(amount0_raw, amount1_raw),
            is_deposit=is_deposit,
        )) is None:
            try:
                position = self.node_inquirer.call_contract(
                    contract_address=PROJECT_X_NFT_MANAGER,
                    abi=PROJECT_X_NFT_MANAGER_ABI,
                    method_name='positions',
                    arguments=[position_id],
                    block_identifier=context.transaction.block_number,
                )
            except (RemoteError, BlockchainQueryError) as e:
                log.error('Failed to query Project X position %s due to %s', position_id, e)
                return DEFAULT_EVM_DECODING_OUTPUT

            token0_address, token1_address = position[2], position[3]
        else:
            (token0_address, amount0_raw), (token1_address, amount1_raw) = token_data

        decoding_output = decode_uniswap_v3_like_deposit_or_withdrawal(
            context=context,
            is_deposit=is_deposit,
            counterparty=CPT_PROJECT_X,
            token0_raw_address=token0_address,
            token1_raw_address=token1_address,
            amount0_raw=amount0_raw,
            amount1_raw=amount1_raw,
            position_id=position_id,
            evm_inquirer=self.node_inquirer,
            display_name='Project X',
        )
        if is_fee_collection is False:
            return decoding_output

        notes = f'Collect {{amount}} {{symbol}} as Project X LP fees for position {position_id}'
        for event in context.decoded_events:
            if (
                    event.event_type != HistoryEventType.WITHDRAWAL or
                    event.event_subtype != HistoryEventSubType.WITHDRAW_FROM_PROTOCOL or
                    event.counterparty != CPT_PROJECT_X
            ):
                continue

            event.event_type = HistoryEventType.RECEIVE
            event.event_subtype = HistoryEventSubType.REWARD
            event.notes = notes.format(
                amount=event.amount,
                symbol=event.asset.symbol_or_name(),
            )

        for action_item in decoding_output.action_items:
            action_item.to_event_type = HistoryEventType.RECEIVE
            action_item.to_event_subtype = HistoryEventSubType.REWARD
            action_item.to_notes = notes

        return decoding_output

    def _lp_post_decoding(
            self,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            all_logs: list[EvmTxReceiptLog],
    ) -> list[EvmEvent]:
        decoded_events = decode_uniswap_v3_like_position_create_or_exit(
            decoded_events=decoded_events,
            evm_inquirer=self.node_inquirer,
            nft_manager=PROJECT_X_NFT_MANAGER,
            counterparty=CPT_PROJECT_X,
            token_symbol='PRJX-V3-POS',
            token_name='Project X V3 Positions',
            display_name='Project X',
        )
        if self._fee_collection_count(all_logs) <= 1:
            return decoded_events

        for event in decoded_events:
            if (
                    event.event_type != HistoryEventType.RECEIVE or
                    event.event_subtype != HistoryEventSubType.NONE or
                    event.address != PROJECT_X_NFT_MANAGER
            ):
                continue

            event.event_type = HistoryEventType.RECEIVE
            event.event_subtype = HistoryEventSubType.REWARD
            event.counterparty = CPT_PROJECT_X
            event.notes = (
                f'Collect {event.amount} {event.asset.symbol_or_name()} as Project X LP fees'
            )

        return decoded_events

    @staticmethod
    def _swap_post_decoding(
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> list[EvmEvent]:
        if transaction.to_address != PROJECT_X_SWAP_ROUTER:
            return decoded_events

        return decode_uniswap_v3_like_router_swap(
            transaction=transaction,
            decoded_events=decoded_events,
            counterparty=CPT_PROJECT_X,
            spend_notes='Swap {amount} {symbol} in Project X',
            receive_notes='Receive {amount} {symbol} as the result of a swap in Project X',
        )

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {PROJECT_X_NFT_MANAGER: (self._decode_liquidity,)}

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_PROJECT_X: [
            (0, self._lp_post_decoding),
            (1, self._swap_post_decoding),
        ]}

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return {PROJECT_X_SWAP_ROUTER: CPT_PROJECT_X}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_PROJECT_X,
            label='Project X',
            image='project-x.svg',
            darkmode_image='project-x_dark.svg',
        ),)
