import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.asset import CryptoAsset, EvmToken, FVal
from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.modules.sushiswap.constants import CPT_SUSHISWAP
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ZERO
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    REDSNWAP_ADDRESS,
    REDSNWAP_ROUTE_PROCESSOR_TOPIC,
    ROUTE_PROCESSOR_TOPIC,
    SUSHISWAP_ICON,
    TOKEN_CHOMPER_ADDRESS,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.chain.evm.types import ChecksumEvmAddress
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import EvmTransaction

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SushiswapCommonDecoder(EvmDecoderInterface):
    """Common decoder for Sushiswap across all EVM chains.

    Handles the RedSnwapper (RP5/RP6) and older Route Processor (RP3/RP3.2/RP4) events.
    Chain-specific decoders inherit from this and can add extra route processor addresses.
    """

    def __init__(
            self,
            extra_route_processors: tuple['ChecksumEvmAddress', ...] = (),
            **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.route_processors: Final = (REDSNWAP_ADDRESS,) + extra_route_processors

    def _decode_swap_event(self, context: DecoderContext) -> EvmDecodingOutput:
        """Identify Sushiswap RedSnwap or Route Processor swap events for post-processing."""
        if context.tx_log.topics[0] in (REDSNWAP_ROUTE_PROCESSOR_TOPIC, ROUTE_PROCESSOR_TOPIC):
            return EvmDecodingOutput(matched_counterparty=CPT_SUSHISWAP)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _handle_post_decoding(
            self,
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        """Process swap events to create proper trade events and fees."""
        tx_log = None
        for i_tx_log in all_logs:
            if i_tx_log.topics[0] == REDSNWAP_ROUTE_PROCESSOR_TOPIC:
                return self._handle_redsnwap_post_decoding(
                    tx_log=i_tx_log,
                    transaction=transaction,
                    decoded_events=decoded_events,
                    all_logs=all_logs,
                )
            if i_tx_log.topics[0] == ROUTE_PROCESSOR_TOPIC:
                tx_log = i_tx_log

        if tx_log is not None:
            return self._handle_route_post_decoding(
                tx_log=tx_log,
                transaction=transaction,
                decoded_events=decoded_events,
            )

        log.error(f'Failed to find Sushiswap route event in transaction {transaction}. This should not happen')  # noqa: E501
        return decoded_events

    def _handle_redsnwap_post_decoding(
            self,
            tx_log: 'EvmTxReceiptLog',
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        """Process RedSnwap (RP5/RP6) swap events."""
        amount_out = asset_normalized_value(
            amount=int.from_bytes(tx_log.data[64:96]),
            asset=(asset_out := self.base.get_token_or_native(bytes_to_address(tx_log.topics[2]))),
        )
        amount_in = asset_normalized_value(
            amount=int.from_bytes(tx_log.data[96:128]),
            asset=(asset_in := self.base.get_token_or_native(amount_in_raw_address := bytes_to_address(tx_log.data[32:64]))),  # noqa: E501
        )
        out_event = in_event = None
        fee_amount, fee_event = self._retrieve_redsnwap_fee(
            asset=asset_in,
            all_logs=all_logs,
            transaction=transaction,
            decoded_events=decoded_events,
            asset_address=amount_in_raw_address,
        )
        actual_amount_received = amount_in - fee_amount
        for event in decoded_events:
            if (
                out_event is None and
                (
                    (event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE) or  # noqa: E501
                    (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.SPEND)  # noqa: E501
                ) and
                event.asset == asset_out and
                event.amount == amount_out
            ):
                out_event = event
                event.counterparty = CPT_SUSHISWAP
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.notes = f'Swap {event.amount} {asset_out.symbol} in Sushiswap'

            elif (
                in_event is None and
                (
                    (event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE) or  # noqa: E501
                    (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.RECEIVE)  # noqa: E501
                ) and
                event.asset == asset_in and
                event.amount == actual_amount_received
            ):
                in_event = event
                event.amount = amount_in
                event.counterparty = CPT_SUSHISWAP
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {amount_in} {asset_in.symbol} from Sushiswap swap'

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event, fee_event],
            events_list=decoded_events,
        )
        return decoded_events

    def _handle_route_post_decoding(
            self,
            tx_log: 'EvmTxReceiptLog',
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
    ) -> list['EvmEvent']:
        """Process older Route Processor (RP3/RP3.2/RP4) swap events.

        Route event format:
        Route(address indexed from, address indexed tokenIn, address indexed tokenOut,
              address to, uint256 amountIn, uint256 amountOutMin, uint256 amountOut)
        """
        # topics[1]=from, topics[2]=tokenIn (what user spends), topics[3]=tokenOut (what user gets)
        asset_out = self.base.get_token_or_native(bytes_to_address(tx_log.topics[2]))
        asset_in = self.base.get_token_or_native(bytes_to_address(tx_log.topics[3]))
        amount_out = asset_normalized_value(
            amount=int.from_bytes(tx_log.data[32:64]),
            asset=asset_out,
        )
        amount_in = asset_normalized_value(
            amount=int.from_bytes(tx_log.data[96:128]),
            asset=asset_in,
        )
        out_event = in_event = None
        for event in decoded_events:
            if (
                out_event is None and
                (
                    (event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE) or  # noqa: E501
                    (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.SPEND)  # noqa: E501
                ) and
                event.asset == asset_out and
                event.amount == amount_out
            ):
                out_event = event
                event.counterparty = CPT_SUSHISWAP
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.notes = f'Swap {event.amount} {asset_out.symbol} in Sushiswap'

            elif (
                in_event is None and
                (
                    (event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE) or  # noqa: E501
                    (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.RECEIVE)  # noqa: E501
                ) and
                event.asset == asset_in and
                event.amount == amount_in
            ):
                in_event = event
                event.counterparty = CPT_SUSHISWAP
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {amount_in} {asset_in.symbol} from Sushiswap swap'

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=decoded_events,
        )
        return decoded_events

    def _retrieve_redsnwap_fee(
            self,
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
            asset: 'CryptoAsset | EvmToken',
            asset_address: 'ChecksumEvmAddress',
    ) -> tuple[FVal, 'EvmEvent | None']:
        """Retrieve and create the fee event for Sushiswap RedSnwap swaps."""
        fee, fee_event = ZERO, None
        if asset_address == ETH_SPECIAL_ADDRESS:
            internal_txs = DBEvmTx(self.node_inquirer.database).get_evm_internal_transactions(
                parent_tx_hash=transaction.tx_hash,
                blockchain=self.node_inquirer.blockchain,
                parent_tx_id=transaction.db_id,
            )
            if len(internal_txs) == 0:
                return fee, fee_event

            for internal_tx in internal_txs:
                if (
                        internal_tx.from_address in self.route_processors and
                        internal_tx.to_address is not None and internal_tx.to_address == TOKEN_CHOMPER_ADDRESS  # noqa: E501
                ):
                    fee += asset_normalized_value(
                        amount=internal_tx.value,
                        asset=asset,
                    )
        else:
            for tx_log in all_logs:
                if (
                    tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                    tx_log.address == asset_address and
                    bytes_to_address(tx_log.topics[1]) in self.route_processors and
                    not self.base.is_tracked(bytes_to_address(tx_log.topics[2]))
                ):
                    fee += asset_normalized_value(
                        amount=int.from_bytes(tx_log.data),
                        asset=asset,
                    )

        if fee > ZERO:
            fee_event = self.base.make_event_next_index(
                tx_ref=transaction.tx_hash,
                timestamp=transaction.timestamp,
                location_label=transaction.from_address,
                asset=asset,
                amount=fee,
                notes=f'Spend {fee} {asset.symbol} as Sushiswap swap fee',
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.FEE,
                counterparty=CPT_SUSHISWAP,
            )
            decoded_events.append(fee_event)

        return fee, fee_event

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return dict.fromkeys(self.route_processors, (self._decode_swap_event,))

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_SUSHISWAP: [(0, self._handle_post_decoding)]}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_SUSHISWAP,
            label='Sushiswap',
            image=SUSHISWAP_ICON,
        ),)
