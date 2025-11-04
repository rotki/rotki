import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal

from eth_typing.abi import ABI

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.quickswap.constants import CPT_QUICKSWAP_V3
from rotkehlchen.chain.evm.decoding.quickswap.utils import decode_quickswap_swap
from rotkehlchen.chain.evm.decoding.quickswap.v3.constants import (
    CPT_QUICKSWAP_V3_ROUTER,
    QUICKSWAP_COLLECT_LIQUIDITY_TOPIC,
    QUICKSWAP_INCREASE_LIQUIDITY_TOPIC,
    QUICKSWAP_V3_NFT_MANAGER_ABI,
)
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
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
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Quickswapv3LikeLPDecoder(EvmDecoderInterface):
    """Common decoder for Quickswap v3 and v4 LP deposits and withdrawals."""

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            nft_manager: 'ChecksumEvmAddress',
            nft_manager_abi: ABI,
            counterparty: Literal['quickswap-v3', 'quickswap-v4'],
            version_string: Literal['V3', 'V4'],
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.nft_manager = nft_manager
        self.nft_manager_abi = nft_manager_abi
        self.counterparty = counterparty
        self.version_string = version_string

    def _decode_deposits_and_withdrawals(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == QUICKSWAP_INCREASE_LIQUIDITY_TOPIC:
            is_deposit = True
            amount0_raw = int.from_bytes(context.tx_log.data[64:96])
            amount1_raw = int.from_bytes(context.tx_log.data[96:128])
        elif context.tx_log.topics[0] == QUICKSWAP_COLLECT_LIQUIDITY_TOPIC:
            is_deposit = False
            amount0_raw = int.from_bytes(context.tx_log.data[32:64])
            amount1_raw = int.from_bytes(context.tx_log.data[64:96])
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        position_id = int.from_bytes(context.tx_log.topics[1])
        try:
            # Returns LP position info in a tuple starting as follows:
            # nonce, operator, token0, token1, ...
            # The other values differ depending on the version (we only use token0 & token1).
            # V3: https://docs.quickswap.exchange/technical-reference/smart-contracts/v3/position-manager#positions  # noqa: E501
            # V4: see QUICKSWAP_V4_NFT_MANAGER_ABI (the quickswap docs do not yet include V4 technical reference)  # noqa: E501
            lp_position_info = self.node_inquirer.call_contract(
                contract_address=self.nft_manager,
                abi=self.nft_manager_abi,
                method_name='positions',
                arguments=[position_id],
            )
        except RemoteError as e:
            log.error(
                f'Failed to query {self.counterparty} nft contract for '
                f'position {position_id} due to {e!s}',
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        return decode_uniswap_v3_like_deposit_or_withdrawal(
            context=context,
            is_deposit=is_deposit,
            counterparty=self.counterparty,
            token0_raw_address=lp_position_info[2],
            token1_raw_address=lp_position_info[3],
            amount0_raw=amount0_raw,
            amount1_raw=amount1_raw,
            position_id=position_id,
            evm_inquirer=self.node_inquirer,
        )

    def _lp_post_decoding(
            self,
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],  # pylint: disable=unused-argument
    ) -> list['EvmEvent']:
        """Update the lp position creation event and position token.
        Note that Quickswap v3/v4 use Algebra dynamic fees (https://docs.algebra.finance/algebra-integral-documentation)
        and the original token name and symbol are `Algebra Positions NFT-V1 (ALGB-POS)`.
        To clarify what protocol this token is actually from, we add quickswap to the name and symbol.
        """  # noqa: E501
        return decode_uniswap_v3_like_position_create_or_exit(
            decoded_events=decoded_events,
            evm_inquirer=self.node_inquirer,
            nft_manager=self.nft_manager,
            counterparty=self.counterparty,
            token_symbol=f'QKSWP-{self.version_string}-ALGB-POS',
            token_name=f'Quickswap {self.version_string} Algebra Positions',
        )

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.nft_manager: (self._decode_deposits_and_withdrawals,)}

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {self.counterparty: [(0, self._lp_post_decoding)]}


class Quickswapv3CommonDecoder(Quickswapv3LikeLPDecoder):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            router_address: 'ChecksumEvmAddress',
            nft_manager: 'ChecksumEvmAddress',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            nft_manager=nft_manager,
            nft_manager_abi=QUICKSWAP_V3_NFT_MANAGER_ABI,
            counterparty=CPT_QUICKSWAP_V3,
            version_string='V3',
        )
        self.router_address = router_address

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

    # -- DecoderInterface methods

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return super().post_decoding_rules() | {
            CPT_QUICKSWAP_V3_ROUTER: [(0, self._v3_router_post_decoding)],
        }

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return {self.router_address: CPT_QUICKSWAP_V3_ROUTER}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails.from_versioned_counterparty(
            counterparty=CPT_QUICKSWAP_V3,
            image='quickswap.png',
        ),)
