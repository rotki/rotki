import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import (
    CounterpartyDetails,
    get_versioned_counterparty_label,
)
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.uniswap.constants import (
    CPT_UNISWAP_V2,
    CPT_UNISWAP_V3,
    UNISWAP_ICON,
)
from rotkehlchen.chain.evm.decoding.uniswap.utils import (
    decode_basic_uniswap_info,
    decode_uniswap_v3_like_position_create_or_exit,
    get_uniswap_swap_amounts,
)
from rotkehlchen.chain.evm.decoding.uniswap.v3.constants import (
    COLLECT_LIQUIDITY_SIGNATURE,
    CPT_UNISWAP_V3_ROUTER,
    INCREASE_LIQUIDITY_SIGNATURE,
    SWAP_SIGNATURE,
)
from rotkehlchen.chain.evm.decoding.uniswap.v3.utils import (
    decode_uniswap_v3_like_deposit_or_withdrawal,
    decode_uniswap_v3_like_router_swap,
)
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import (
        ChecksumEvmAddress,
        EvmTransaction,
    )
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Uniswapv3CommonDecoder(EvmDecoderInterface):

    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
            routers_addresses: set[ChecksumEvmAddress],
            nft_manager: ChecksumEvmAddress,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.routers_addresses = routers_addresses
        self.nft_manager = nft_manager

    def _decode_deposits_and_withdrawals(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == INCREASE_LIQUIDITY_SIGNATURE:
            is_deposit = True
        elif context.tx_log.topics[0] == COLLECT_LIQUIDITY_SIGNATURE:
            is_deposit = False
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        position_id = int.from_bytes(context.tx_log.topics[1])
        try:
            # Returns a tuple containing information about the state of the LP position.
            # https://docs.uniswap.org/contracts/v3/reference/periphery/NonfungiblePositionManager#positions
            # 0 -> position.nonce,
            # 1 -> position.operator,
            # 2 -> poolKey.token0, <--- Used. The first token in the pool
            # 3 -> poolKey.token1, <--- Used. The second token in the pool
            # 4 -> poolKey.fee,
            # 5 -> position.tickLower,
            # 6 -> position.tickUpper,
            # 7 -> position.liquidity,
            # 8 -> position.feeGrowthInside0LastX128,
            # 9 -> position.feeGrowthInside1LastX128,
            # 10 -> position.tokensOwed0,
            # 11 -> position.tokensOwed1
            lp_position_info = self.node_inquirer.contracts.contract(self.nft_manager).call(
                node_inquirer=self.node_inquirer,
                method_name='positions',
                arguments=[position_id],
            )
        except RemoteError as e:
            log.error(
                'Failed to query uniswap v3 nft contract for '
                f'position {position_id} due to {e!s}',
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        return decode_uniswap_v3_like_deposit_or_withdrawal(
            context=context,
            is_deposit=is_deposit,
            counterparty=CPT_UNISWAP_V3,
            token0_raw_address=lp_position_info[2],
            token1_raw_address=lp_position_info[3],
            amount0_raw=int.from_bytes(context.tx_log.data[32:64]),
            amount1_raw=int.from_bytes(context.tx_log.data[64:96]),
            position_id=position_id,
            evm_inquirer=self.node_inquirer,
        )

    def _maybe_decode_v3_swap(
            self,
            token: EvmToken | None,  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list[EvmEvent],
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> EvmDecodingOutput:
        """
        Detect some basic uniswap v3 events. This method doesn't ensure the order of the events
        and other things, but just labels some of the events as uniswap v3 events.
        The order should be ensured by the post-decoding rules.
        """
        if tx_log.topics[0] != SWAP_SIGNATURE:
            return DEFAULT_EVM_DECODING_OUTPUT

        amount_received, amount_sent = get_uniswap_swap_amounts(tx_log=tx_log)

        # Uniswap V3 pools are used with complex routers/aggregators and there can be
        # multiple spend and multiple receive events that are hard to decode by looking only
        # at a single swap event. Because of that here we decode only basic info, leaving the rest
        # of the work to the router/aggregator-specific decoding methods.
        return decode_basic_uniswap_info(
            amount_sent=amount_sent,
            amount_received=amount_received,
            decoded_events=decoded_events,
            counterparty=CPT_UNISWAP_V3,
            notify_user=self.notify_user,
            native_currency=self.node_inquirer.native_token,
        )

    def _routers_post_decoding(
            self,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> list[EvmEvent]:
        """
        Ensures that if an auto router (either v1 or v2) is used, events have correct order and
        are properly combined (i.e. each swap consists only of one spend and one receive event).

        Right now supports only swaps that are made through official uniswap auto routers and have
        only one source / destination token.

        If it fails to decode a swap, it will return the original list of events.

        This function checks for three types of swaps:
        1. Swap from native currency to token
        2. Swap from token to native currency
        3. Swap from token to token (with a single receive or multiple receive events)
        """
        if transaction.to_address not in self.routers_addresses:
            return decoded_events  # work only with the known routers for now
        display_name = get_versioned_counterparty_label(CPT_UNISWAP_V3)
        return decode_uniswap_v3_like_router_swap(
            transaction=transaction,
            decoded_events=decoded_events,
            counterparty=CPT_UNISWAP_V3,
            spend_notes=f'Swap {{amount}} {{symbol}} via {display_name} auto router',
            receive_notes=f'Receive {{amount}} {{symbol}} as the result of a swap via {display_name} auto router',  # noqa: E501
            source_counterparties={CPT_UNISWAP_V2, CPT_UNISWAP_V3},
            retain_non_swap_events=False,
        )

    def _lp_post_decoding(
            self,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> list[EvmEvent]:
        """Update the lp position creation event and position token."""
        return decode_uniswap_v3_like_position_create_or_exit(
            decoded_events=decoded_events,
            evm_inquirer=self.node_inquirer,
            nft_manager=self.nft_manager,
            counterparty=CPT_UNISWAP_V3,
            token_symbol='UNI-V3-POS',
            token_name='Uniswap V3 Positions',
        )

    # -- DecoderInterface methods

    def decoding_rules(self) -> list[Callable]:
        return [self._maybe_decode_v3_swap]

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.nft_manager: (self._decode_deposits_and_withdrawals,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails.from_versioned_counterparty(
            counterparty=CPT_UNISWAP_V3,
            image=UNISWAP_ICON,
        ),)

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {
            CPT_UNISWAP_V3: [(0, self._lp_post_decoding)],
            CPT_UNISWAP_V3_ROUTER: [(0, self._routers_post_decoding)],
        }

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return dict.fromkeys(self.routers_addresses, CPT_UNISWAP_V3_ROUTER)
