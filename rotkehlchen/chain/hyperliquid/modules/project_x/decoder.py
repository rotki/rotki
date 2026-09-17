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
    INCREASE_LIQUIDITY_SIGNATURE,
    POOL_COLLECT_SIGNATURE,
    POOL_MINT_SIGNATURE,
)
from rotkehlchen.chain.evm.decoding.uniswap.v3.utils import (
    decode_uniswap_v3_like_deposit_or_withdrawal,
    decode_uniswap_v3_like_router_swap,
)
from rotkehlchen.errors.misc import BlockchainQueryError, RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    CPT_PROJECT_X,
    PROJECT_X_NFT_MANAGER,
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
        if context.tx_log.topics[0] == INCREASE_LIQUIDITY_SIGNATURE:
            is_deposit = True
        elif context.tx_log.topics[0] == COLLECT_LIQUIDITY_SIGNATURE:
            is_deposit = False
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        amounts = (
            int.from_bytes(context.tx_log.data[32:64]),
            int.from_bytes(context.tx_log.data[64:96]),
        )
        if (token_data := self._get_transfer_token_data(
            all_logs=context.all_logs, amounts=amounts, is_deposit=is_deposit,
        )) is not None:
            (token0_address, amount0_raw), (token1_address, amount1_raw) = token_data
        else:
            # Pool logs retain the token source after an NFT is burned, without archive state.
            pool_topic = POOL_MINT_SIGNATURE if is_deposit else POOL_COLLECT_SIGNATURE
            for tx_log in reversed(context.all_logs):
                if (
                    tx_log.log_index < context.tx_log.log_index and
                    len(tx_log.topics) >= 2 and
                    tx_log.topics[0] == pool_topic and
                    bytes_to_address(tx_log.topics[1]) == PROJECT_X_NFT_MANAGER and
                    (amount0_raw := int.from_bytes(tx_log.data[-64:-32])) <= amounts[0] and
                    (amount1_raw := int.from_bytes(tx_log.data[-32:])) <= amounts[1] and
                    (is_deposit or tx_log.data[:32] == context.tx_log.data[:32])
                ):
                    break
            else:
                log.error('Could not find Project X liquidity pool in %s', context.transaction.tx_hash.hex())  # noqa: E501
                return DEFAULT_EVM_DECODING_OUTPUT

            try:
                token0_address, token1_address = (
                    deserialize_evm_address(self.node_inquirer.call_contract(
                        contract_address=tx_log.address,
                        abi=self.node_inquirer.contracts.abi('UNISWAP_V3_POOL'),
                        method_name=method,
                    )) for method in ('token0', 'token1')
                )
            except (RemoteError, BlockchainQueryError) as e:
                log.error('Failed to query Project X pool tokens: %s', e)
                return DEFAULT_EVM_DECODING_OUTPUT

        return decode_uniswap_v3_like_deposit_or_withdrawal(
            context=context,
            is_deposit=is_deposit,
            counterparty=CPT_PROJECT_X,
            token0_raw_address=token0_address,
            token1_raw_address=token1_address,
            amount0_raw=amount0_raw,
            amount1_raw=amount1_raw,
            position_id=int.from_bytes(context.tx_log.topics[1]),
            evm_inquirer=self.node_inquirer,
            display_name='Project X',
        )

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
        if sum(
            tx_log.address == PROJECT_X_NFT_MANAGER and
            tx_log.topics[0] == COLLECT_LIQUIDITY_SIGNATURE
            for tx_log in all_logs
        ) <= 1:
            return decoded_events

        for event in decoded_events:
            if (
                    event.event_type != HistoryEventType.RECEIVE or
                    event.event_subtype != HistoryEventSubType.NONE or
                    event.address != PROJECT_X_NFT_MANAGER
            ):
                continue

            event.event_type = HistoryEventType.WITHDRAWAL
            event.event_subtype = HistoryEventSubType.WITHDRAW_FROM_PROTOCOL
            event.counterparty = CPT_PROJECT_X
            event.extra_data = (event.extra_data or {}) | {'liquidity_pool': True}
            event.notes = (
                f'Collect {event.amount} {event.asset.symbol_or_name()} '
                'from Project X LP positions'
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
