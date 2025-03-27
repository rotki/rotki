import logging
from typing import Any

from rotkehlchen.chain.ethereum.utils import (
    asset_normalized_value,
    token_normalized_value_decimals,
)
from rotkehlchen.chain.evm.constants import (
    DEFAULT_TOKEN_DECIMALS,
)
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    ADD_LIQUIDITY_TOPIC,
    CPT_PENDLE,
    KYBERSWAP_SWAPPED_TOPIC,
    ODOS_SWAP_TOPIC,
    OKX_ORDER_RECORD_TOPIC,
    PENDLE_ROUTER_ABI,
    PENDLE_ROUTER_ADDRESS,
    PENDLE_SWAP_ADDRESS,
    REMOVE_LIQUIDITY_TOPIC,
    SWAP_SINGLE_TOPIC,
    SWAP_TOKEN_FOR_PT_TOPIC,
    SWAP_TOKEN_FOR_YT_TOPIC,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class PendleCommonDecoder(DecoderInterface):

    def _decode_pendle_events(self, context: DecoderContext) -> DecodingOutput:
        """This method decodes the following pendle events:
        1. Buy or sell principal token(PT) with/for yield token (e.g. sUSDe, LBTC)
        2. Buy or sell yield token(YT) with/for yield token (e.g. sUSDe, LBTC)
        3. Adding or removing liquidity.
        """
        if context.tx_log.topics[0] in (SWAP_TOKEN_FOR_PT_TOPIC, SWAP_TOKEN_FOR_YT_TOPIC):
            return self._decode_pt_yt_events(context)
        elif context.tx_log.topics[0] == ADD_LIQUIDITY_TOPIC:
            return self._decode_add_liquidity_event(context)
        elif context.tx_log.topics[0] == REMOVE_LIQUIDITY_TOPIC:
            return self._decode_remove_liquidity_event(context)

        return DEFAULT_DECODING_OUTPUT

    def _decode_add_liquidity_event(self, context: DecoderContext) -> DecodingOutput:
        """This method decodes adding liquidity to a Pendle LP"""
        deposited_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[32:64]),
            asset=(deposited_token := self.base.get_token_or_native(bytes_to_address(context.tx_log.topics[3]))),  # noqa: E501
        )
        received_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[64:96]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        for event in context.decoded_events:
            if event.amount == deposited_amount and event.event_type == HistoryEventType.SPEND:
                event.counterparty = CPT_PENDLE
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.notes = f'Deposit {event.amount} {deposited_token.symbol} in a Pendle pool'

            elif event.amount == received_amount and event.event_type == HistoryEventType.RECEIVE:
                event.counterparty = CPT_PENDLE
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.notes = f'Receive {received_amount} PENDLE-LPT for depositing in a Pendle pool'  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_remove_liquidity_event(self, context: DecoderContext) -> DecodingOutput:
        """This method decodes removing liquidity from a Pendle LP"""
        received_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[64:96]),
            asset=(received_token := self.base.get_or_create_evm_token(bytes_to_address(context.tx_log.topics[3]))),  # noqa: E501
        )
        returned_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        for event in context.decoded_events:
            if event.amount == returned_amount and event.event_type == HistoryEventType.SPEND:
                event.counterparty = CPT_PENDLE
                event.event_type = HistoryEventType.SPEND
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.notes = f'Return {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} to Pendle'  # noqa: E501

            elif event.amount == received_amount and event.event_type == HistoryEventType.RECEIVE:
                event.counterparty = CPT_PENDLE
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.notes = f'Withdraw {event.amount} {received_token.symbol} from a Pendle pool'

        return DEFAULT_DECODING_OUTPUT

    def _decode_pt_yt_events(self, context: DecoderContext) -> DecodingOutput:
        """Decode Pendle market events for buying or selling Principal (PT) or Yield (YT) tokens.

        This method handles two primary scenarios:
        - Buying PT/YT: token_0 is spent, token_1 is received
        - Selling PT/YT: token_0 is received, token_1 is spent
        """
        market = bytes_to_address(context.tx_log.topics[2])
        _, principal_token, yield_token = self.evm_inquirer.call_contract(
            contract_address=market,
            abi=PENDLE_ROUTER_ABI,
            method_name='readTokens',
        )
        amount_0 = asset_normalized_value(
            amount=abs(int.from_bytes(context.tx_log.data[64:96], signed=True)),
            asset=(token_0 := self.base.get_token_or_native(bytes_to_address(context.tx_log.topics[3]))),  # noqa: E501
        )
        token_1 = self.base.get_or_create_evm_token(principal_token if context.tx_log.topics[0] == SWAP_TOKEN_FOR_PT_TOPIC else yield_token)  # noqa: E501
        amount_1 = asset_normalized_value(
            amount=abs(int.from_bytes(context.tx_log.data[32:64], signed=True)),
            asset=token_1,
        )
        for event in context.decoded_events:
            if event.asset == token_0 and event.amount == amount_0:
                # When zapping into PT/YT, a swap event is followed by a deposit event.
                # This logic ensures we correctly map those sequences depending on direction.
                if (
                        event.event_type in (HistoryEventType.SPEND, HistoryEventType.TRADE) and
                        event.event_subtype in (HistoryEventSubType.NONE, HistoryEventSubType.SPEND)  # noqa: E501
                ):
                    event.counterparty = CPT_PENDLE
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                    event.extra_data = {'market': market}
                    event.notes = f'Deposit {event.amount} {token_0.symbol} to Pendle'
                elif event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE:  # noqa: E501
                    event.counterparty = CPT_PENDLE
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                    event.notes = f'Withdraw {event.amount} {token_0.symbol} from Pendle'

            elif event.asset == token_1 and event.amount == amount_1:
                if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE:  # noqa: E501
                    event.counterparty = CPT_PENDLE
                    event.event_type = HistoryEventType.RECEIVE
                    event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                    event.notes = f'Receive {amount_1} {token_1.symbol} from depositing into Pendle'  # noqa: E501
                elif event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE:  # noqa: E501
                    event.counterparty = CPT_PENDLE
                    event.event_type = HistoryEventType.SPEND
                    event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                    event.notes = f'Return {event.amount} {token_1.symbol} to Pendle'

        return DEFAULT_DECODING_OUTPUT

    def _decode_pendle_swap(self, context: DecoderContext) -> DecodingOutput:
        """This decodes swap events that use the PendleSwap contract.

        Below are aggregators used by PendleSwap with their indexes:
        Kyberswap -> 1
        Odos -> 2
        Okx -> 4
        1inch -> 5

        Data is gotten from:
        https://github.com/pendle-finance/pendle-core-v2-public/blob/761033bcc36ecfdb3c523458d7f66aeabb01c3ab/contracts/router/swap-aggregator/IPSwapAggregator.sol#L18
        """
        if context.tx_log.topics[0] != SWAP_SINGLE_TOPIC:
            return DEFAULT_DECODING_OUTPUT

        # Determine swap type and retrieve received token details.
        # Pendle only emits an event for the token being swapped,
        # so we must check transaction logs to find the received token
        amount_out = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[:32]),
            asset=(token_out := self.base.get_token_or_native(bytes_to_address(context.tx_log.topics[2]))),  # noqa: E501
        )
        if (swap_type := int.from_bytes(context.tx_log.topics[1])) == 1:
            expected_log_topic = KYBERSWAP_SWAPPED_TOPIC
        elif swap_type == 2:
            expected_log_topic = ODOS_SWAP_TOPIC
        elif swap_type == 4:
            expected_log_topic = OKX_ORDER_RECORD_TOPIC
        else:
            # TODO: Check for transactions for swap_type=5 (1inch).
            # Currently skipped — see note: https://github.com/orgs/rotki/projects/11/views/2?pane=issue&itemId=104045988
            log.debug(f'Found an unsupported swap type {swap_type} in transaction {context.transaction}')  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        for tx_log in context.all_logs:
            if tx_log.topics[0] != expected_log_topic:
                continue

            if bytes_to_address(tx_log.data[96:128]) == PENDLE_ROUTER_ADDRESS:  # kyberswap
                amount_in = asset_normalized_value(
                    amount=int.from_bytes(tx_log.data[160:192]),
                    asset=(token_in := self.base.get_token_or_native(bytes_to_address(tx_log.data[64:96]))),  # noqa: E501
                )
                break

            elif bytes_to_address(tx_log.data[:32]) == PENDLE_SWAP_ADDRESS:  # odos
                amount_in = asset_normalized_value(
                    amount=int.from_bytes(tx_log.data[96:128]),
                    asset=(token_in := self.base.get_token_or_native(bytes_to_address(tx_log.data[128:160]))),  # noqa: E501
                )
                break

            else:  # okx
                amount_in = asset_normalized_value(
                    amount=int.from_bytes(tx_log.data[128:160]),
                    asset=(token_in := self.base.get_token_or_native(bytes_to_address(tx_log.data[32:64]))),  # noqa: E501
                )
                break
        else:
            log.error(f'Could not retrieve swap details for {swap_type=} in transaction {context.transaction}')  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        in_event, out_event = None, None
        for event in context.decoded_events:
            if (
                    event.asset == token_out and
                    event.amount == amount_out and
                    event.address == PENDLE_ROUTER_ADDRESS and
                    event.event_type in (HistoryEventType.SPEND, HistoryEventType.TRADE) and
                    event.event_subtype in (HistoryEventSubType.NONE, HistoryEventSubType.SPEND)
            ):
                out_event = event
                event.counterparty = CPT_PENDLE
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.notes = f'Swap {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} in Pendle'  # noqa: E501

            elif (
                    event.asset == token_in and
                    event.amount == amount_in and
                    event.address == PENDLE_ROUTER_ADDRESS and
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE
            ):
                in_event = event
                event.counterparty = CPT_PENDLE
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {event.amount} {token_in.symbol} from Pendle swap'

        if in_event is None and out_event is None:
            log.error(f'Could not retrieve both in & out events for pendle swap transaction {context.transaction}')  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        # If the received token isn't the native token, we use an action item to match it later,
        # since the receive event occurs after the swap event.
        action_items = []
        if in_event is None and out_event is not None:
            action_items.append(ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                to_event_type=HistoryEventType.TRADE,
                to_event_subtype=HistoryEventSubType.RECEIVE,
                amount=amount_in,
                asset=token_in,
                paired_events_data=([out_event], True),
                to_notes=f'Receive {amount_in} {token_in.symbol} from Pendle swap',
                to_counterparty=CPT_PENDLE,
            ))

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return DecodingOutput(action_items=action_items)

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            PENDLE_ROUTER_ADDRESS: (self._decode_pendle_events,),
            PENDLE_SWAP_ADDRESS: (self._decode_pendle_swap,),
        }

    @staticmethod
    def counterparties() -> tuple['CounterpartyDetails', ...]:
        return (CounterpartyDetails(
            identifier=CPT_PENDLE,
            label='Pendle Finance',
            image='pendle_light.svg',
            darkmode_image='pendle_dark.svg',
        ),)
