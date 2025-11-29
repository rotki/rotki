import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.asset import CryptoAsset, EvmToken, FVal
from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import BURN_TOPIC, ETH_SPECIAL_ADDRESS, MINT_TOPIC
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.uniswap.v2.constants import UNISWAP_V2_SWAP_SIGNATURE
from rotkehlchen.chain.evm.decoding.uniswap.v2.utils import (
    decode_uniswap_like_deposit_and_withdrawals,
    decode_uniswap_v2_like_swap,
)
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import ChecksumEvmAddress, string_to_evm_address
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ZERO, EvmTransaction
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_SUSHISWAP, CPT_SUSHISWAP_V2

if TYPE_CHECKING:
    from rotkehlchen.history.events.structures.evm_event import EvmEvent

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

SUSHISWAP_ROUTER: Final = string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F')
SUSHISWAP_REDSNWAP_ROUTE_PROCESSORS: Final = (  # https://docs.sushi.com/aggregator/introduction
    string_to_evm_address('0x3B0AA7d38Bf3C103bf02d1De2E37568cBED3D6e8'),
    string_to_evm_address('0xd2b37aDE14708bf18904047b1E31F8166d39612b'),
    string_to_evm_address('0x3Ced11c610556e5292fBC2e75D68c3899098C14C'),
    string_to_evm_address('0x2905d7e4D048d29954F81b02171DD313F457a4a4'),
)
# RedSnwapper fee collector that receives token swap fees
TOKEN_CHOMPER_ADDRESS: Final = string_to_evm_address('0xde7259893Af7cdbC9fD806c6ba61D22D581d5667')
REDSNWAP_ROUTE_PROCESSOR_TOPIC: Final = b'\x84\xb5\x14\xc5\xb9&\x87\x9b\xf6j\x04\xe4\xbe\xcd\xc6\xf5!\xe9JD\x11\xe7\xdf\xa3\xdd%_!Dx\xf5X'  # noqa: E501
SUSHISWAP_V2_FACTORY: Final = string_to_evm_address('0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac')
SUSHISWAP_V2_INIT_CODE_HASH: Final = '0xe18a34eb0e04b04f7a0ac29a6e80748dca96319b42c54d679cb821dca90c6303'  # noqa: E501


class SushiswapDecoder(EvmDecoderInterface):

    def _maybe_decode_v2_swap(
            self,
            token: EvmToken | None,  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> EvmDecodingOutput:
        if tx_log.topics[0] == UNISWAP_V2_SWAP_SIGNATURE and transaction.to_address == SUSHISWAP_ROUTER:  # noqa: E501
            return decode_uniswap_v2_like_swap(
                tx_log=tx_log,
                decoded_events=decoded_events,
                transaction=transaction,
                counterparty=CPT_SUSHISWAP_V2,
                router_address=SUSHISWAP_ROUTER,
                database=self.node_inquirer.database,
                evm_inquirer=self.node_inquirer,
                notify_user=self.notify_user,
            )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _maybe_decode_v2_liquidity_addition_and_removal(
            self,
            token: EvmToken | None,  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list['EvmEvent'],
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],
    ) -> EvmDecodingOutput:
        if tx_log.topics[0] == MINT_TOPIC:
            return decode_uniswap_like_deposit_and_withdrawals(
                tx_log=tx_log,
                decoded_events=decoded_events,
                all_logs=all_logs,
                is_deposit=True,
                counterparty=CPT_SUSHISWAP_V2,
                database=self.node_inquirer.database,
                evm_inquirer=self.node_inquirer,
                factory_address=SUSHISWAP_V2_FACTORY,
                init_code_hash=SUSHISWAP_V2_INIT_CODE_HASH,
                tx_hash=transaction.tx_hash,
            )
        if tx_log.topics[0] == BURN_TOPIC:
            return decode_uniswap_like_deposit_and_withdrawals(
                tx_log=tx_log,
                decoded_events=decoded_events,
                all_logs=all_logs,
                is_deposit=False,
                counterparty=CPT_SUSHISWAP_V2,
                database=self.node_inquirer.database,
                evm_inquirer=self.node_inquirer,
                factory_address=SUSHISWAP_V2_FACTORY,
                init_code_hash=SUSHISWAP_V2_INIT_CODE_HASH,
                tx_hash=transaction.tx_hash,
            )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_redsnwap_event(self, context: 'DecoderContext') -> EvmDecodingOutput:
        """Identify Sushiswap RedSnwap swap events for post-processing."""
        if context.tx_log.topics[0] != REDSNWAP_ROUTE_PROCESSOR_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        return EvmDecodingOutput(matched_counterparty=CPT_SUSHISWAP)

    def _handle_post_decoding(
            self,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        """Process RedSnwap swap events to create proper trade events and fees.
        See: https://docs.sushi.com/contracts/red-snwapper
        """
        tx_log = None
        for i_tx_log in all_logs:
            if i_tx_log.topics[0] == REDSNWAP_ROUTE_PROCESSOR_TOPIC:
                tx_log = i_tx_log
                break
        else:
            log.error(f'Failed to find REDSNWAP_ROUTE_PROCESSOR_TOPIC in transaction {transaction}. This should not happen')  # noqa: E501
            return decoded_events

        amount_out = asset_normalized_value(
            amount=int.from_bytes(tx_log.data[64:96]),
            asset=(asset_out := self.base.get_token_or_native(bytes_to_address(tx_log.topics[2]))),
        )
        amount_in = asset_normalized_value(
            amount=int.from_bytes(tx_log.data[96:128]),
            asset=(asset_in := self.base.get_token_or_native(amount_in_raw_address := bytes_to_address(tx_log.data[32:64]))),  # noqa: E501
        )
        out_event = in_event = None
        fee_amount, fee_event = self._retrieve_rednswap_fee(
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

    def _retrieve_rednswap_fee(
            self,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
            asset: 'CryptoAsset | EvmToken',
            asset_address: ChecksumEvmAddress,
    ) -> tuple[FVal, 'EvmEvent | None']:
        """Retrieve and create the fee event for Sushiswap RedSnwap swaps.

        For ETH swaps, fees are collected via internal transactions to TOKEN_CHOMPER_ADDRESS.
        For token swaps, fees are collected via ERC20 transfers to TOKEN_CHOMPER_ADDRESS.
        """
        fee, fee_event = ZERO, None
        if asset_address == ETH_SPECIAL_ADDRESS:
            if (internal_txs := DBEvmTx(self.node_inquirer.database).get_evm_internal_transactions(
                parent_tx_hash=transaction.tx_hash,
                blockchain=self.node_inquirer.blockchain,
            )) == 0:
                return fee, fee_event

            for internal_tx in internal_txs:
                if (
                        internal_tx.from_address in SUSHISWAP_REDSNWAP_ROUTE_PROCESSORS and
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
                    bytes_to_address(tx_log.topics[1]) in SUSHISWAP_REDSNWAP_ROUTE_PROCESSORS and
                    not self.base.is_tracked(bytes_to_address(tx_log.topics[2]))
                ):
                    fee += asset_normalized_value(
                        amount=int.from_bytes(tx_log.data),
                        asset=asset,
                    )

        if fee > ZERO:  # create fee event if there is a fee
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

    def decoding_rules(self) -> list[Callable]:
        return [
            self._maybe_decode_v2_swap,
            self._maybe_decode_v2_liquidity_addition_and_removal,
        ]

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(SUSHISWAP_REDSNWAP_ROUTE_PROCESSORS, (self._decode_redsnwap_event,))

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_SUSHISWAP: [(0, self._handle_post_decoding)]}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_SUSHISWAP_V2,
            label='Sushiswap',
            image='sushiswap.svg',
        ), CounterpartyDetails(
            identifier=CPT_SUSHISWAP,
            label='Sushiswap',
            image='sushiswap.svg',
        ))
