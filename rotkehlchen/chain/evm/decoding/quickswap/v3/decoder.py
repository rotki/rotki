import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import CHAIN_TO_WRAPPED_TOKEN
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.quickswap.constants import CPT_QUICKSWAP_V3
from rotkehlchen.chain.evm.decoding.quickswap.utils import decode_quickswap_swap
from rotkehlchen.chain.evm.decoding.quickswap.v3.constants import (
    CPT_QUICKSWAP_V3_ROUTER,
    QUICKSWAP_COLLECT_LIQUIDITY_TOPIC,
    QUICKSWAP_INCREASE_LIQUIDITY_TOPIC,
    QUICKSWAP_NFT_MANAGER_ABI,
)
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.uniswap.utils import (
    decode_uniswap_v3_like_position_create_or_exit,
)
from rotkehlchen.chain.evm.decoding.uniswap.v3.constants import (
    SWAP_SIGNATURE as UNISWAP_V3_SWAP_SIGNATURE,
)
from rotkehlchen.chain.evm.decoding.uniswap.v3.utils import (
    decode_uniswap_v3_like_deposit_or_withdrawal,
)
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Quickswapv3CommonDecoder(DecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            router_address: 'ChecksumEvmAddress',
            nft_manager: 'ChecksumEvmAddress',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.router_address = router_address
        self.nft_manager = nft_manager
        self.wrapped_native_currency = CHAIN_TO_WRAPPED_TOKEN[evm_inquirer.blockchain]

    def _v3_router_post_decoding(
            self,
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        for tx_log in all_logs:
            if tx_log.topics[0] == UNISWAP_V3_SWAP_SIGNATURE:
                return decode_quickswap_swap(tx_log=tx_log, decoded_events=decoded_events)

        return decoded_events

    def _decode_deposits_and_withdrawals(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == QUICKSWAP_INCREASE_LIQUIDITY_TOPIC:
            is_deposit = True
            amount0_raw = int.from_bytes(context.tx_log.data[64:96])
            amount1_raw = int.from_bytes(context.tx_log.data[96:128])
        elif context.tx_log.topics[0] == QUICKSWAP_COLLECT_LIQUIDITY_TOPIC:
            is_deposit = False
            amount0_raw = int.from_bytes(context.tx_log.data[32:64])
            amount1_raw = int.from_bytes(context.tx_log.data[64:96])
        else:
            return DEFAULT_DECODING_OUTPUT

        position_id = int.from_bytes(context.tx_log.topics[1])
        try:
            # Returns the following LP position info in a tuple:
            # (nonce, operator, token0, token1, tickLower, tickUpper, liquidity,
            # feeGrowthInside0LastX128, feeGrowthInside1LastX128, tokensOwed0, tokensOwed1)
            # https://docs.quickswap.exchange/technical-reference/smart-contracts/v3/position-manager#positions  # noqa: E501
            # This differs from uniswap in that it does not include a `fee` field.
            lp_position_info = self.evm_inquirer.call_contract(
                contract_address=self.nft_manager,
                abi=QUICKSWAP_NFT_MANAGER_ABI,
                method_name='positions',
                arguments=[position_id],
            )
        except RemoteError as e:
            log.error(
                'Failed to query quickswap v3 nft contract for '
                f'position {position_id} due to {e!s}',
            )
            return DEFAULT_DECODING_OUTPUT

        return decode_uniswap_v3_like_deposit_or_withdrawal(
            context=context,
            is_deposit=is_deposit,
            counterparty=CPT_QUICKSWAP_V3,
            token0_raw_address=lp_position_info[2],
            token1_raw_address=lp_position_info[3],
            amount0_raw=amount0_raw,
            amount1_raw=amount1_raw,
            position_id=position_id,
            evm_inquirer=self.evm_inquirer,
            wrapped_native_currency=self.wrapped_native_currency,
        )

    def _lp_post_decoding(
            self,
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],  # pylint: disable=unused-argument
    ) -> list['EvmEvent']:
        """Update the lp position creation event and position token.
        Note that Quickswap v3 uses Algebra dynamic fees (https://docs.algebra.finance/algebra-integral-documentation)
        and the original token name and symbol are `Algebra Positions NFT-V1 (ALGB-POS)`.
        To clarify what protocol this token is actually from, we add quickswap v3 to the name and symbol.
        """  # noqa: E501
        return decode_uniswap_v3_like_position_create_or_exit(
            decoded_events=decoded_events,
            evm_inquirer=self.evm_inquirer,
            nft_manager=self.nft_manager,
            counterparty=CPT_QUICKSWAP_V3,
            token_symbol='QKSWP-V3-ALGB-POS',
            token_name='Quickswap V3 Algebra Positions',
        )

    # -- DecoderInterface methods

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {
            CPT_QUICKSWAP_V3: [(0, self._lp_post_decoding)],
            CPT_QUICKSWAP_V3_ROUTER: [(0, self._v3_router_post_decoding)],
        }

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return {self.router_address: CPT_QUICKSWAP_V3_ROUTER}

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.nft_manager: (self._decode_deposits_and_withdrawals,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails.from_versioned_counterparty(
            counterparty=CPT_QUICKSWAP_V3,
            image='quickswap.png',
        ),)
