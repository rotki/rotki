import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.chain.ethereum.utils import (
    asset_normalized_value,
    asset_raw_value,
    should_update_protocol_cache,
    token_normalized_value_decimals,
)
from rotkehlchen.chain.evm.constants import (
    DEFAULT_TOKEN_DECIMALS,
    ZERO_ADDRESS,
)
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface, ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.globaldb.cache import globaldb_get_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    ADD_LIQUIDITY_TOPIC,
    CPT_PENDLE,
    EXIT_POST_EXP_TO_TOKEN_TOPIC,
    KYBERSWAP_SWAPPED_TOPIC,
    MINT_PT_YT_FROM_TOKEN_TOPIC,
    MINT_SY_FROM_TOKEN_TOPIC,
    ODOS_SWAP_TOPIC,
    OKX_ORDER_RECORD_TOPIC,
    PENDLE_ROUTER_ABI,
    PENDLE_ROUTER_ADDRESS,
    PENDLE_SWAP_ADDRESS,
    REDEEM_PT_YT_TO_TOKEN_TOPIC,
    REDEEM_REWARDS_TOPIC,
    REDEEM_SY_TO_TOKEN_TOPIC,
    REDEEM_TOPIC,
    REMOVE_LIQUIDITY_TOPIC,
    SWAP_SINGLE_TOPIC,
    SWAP_TOKEN_FOR_PT_TOPIC,
    SWAP_TOKEN_FOR_YT_TOPIC,
)
from .utils import query_pendle_markets

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class PendleCommonDecoder(DecoderInterface, ReloadableDecoderMixin):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.pools: set[ChecksumEvmAddress] = set()
        self.sy_tokens: set[ChecksumEvmAddress] = set()

    def _decode_pendle_events(self, context: DecoderContext) -> DecodingOutput:
        """This method decodes the following pendle events:
        1. Swapping tokens for Principal Tokens (PT) or Yield Tokens (YT), and vice versa.
            - PT: Represents the principal portion of a yield-bearing asset.
            - YT: Represents the future yield of the asset, decoupled from the principal.
        2. Minting or redeeming Standardized Yield Tokens(SY), PT, or YT tokens from/to an underlying token.
           - SY tokens wrap yield-bearing assets into a standardized ERC-20 format used within Pendle ecosystem.
        3. Adding or removing liquidity from a Pendle liquidity pool.
        4. Exiting a Pendle pool post-expiration, redeeming expired positions into the underlying asset.
        """  # noqa: E501
        if context.tx_log.topics[0] in (SWAP_TOKEN_FOR_PT_TOPIC, SWAP_TOKEN_FOR_YT_TOPIC):
            return self._decode_pt_yt_events(context)
        elif context.tx_log.topics[0] == ADD_LIQUIDITY_TOPIC:
            return self._decode_add_liquidity_event(context)
        elif context.tx_log.topics[0] == REMOVE_LIQUIDITY_TOPIC:
            return self._decode_remove_liquidity_event(context)
        elif context.tx_log.topics[0] in (MINT_PT_YT_FROM_TOKEN_TOPIC, MINT_SY_FROM_TOKEN_TOPIC):
            return self._decode_mint_sy_pt_yt_from_token(context)
        elif context.tx_log.topics[0] in (REDEEM_PT_YT_TO_TOKEN_TOPIC, REDEEM_SY_TO_TOKEN_TOPIC):
            return self._decode_redeem_sy_pt_yt_to_token(context)
        elif context.tx_log.topics[0] == EXIT_POST_EXP_TO_TOKEN_TOPIC:
            return self._decode_exit_post_exp_to_token(context)

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
        """Decode Pendle market events for buying or selling PT/YT.

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
        out_event, in_event = None, None
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
                    out_event = event
                elif event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE:  # noqa: E501
                    event.counterparty = CPT_PENDLE
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                    event.notes = f'Withdraw {event.amount} {token_0.symbol} from Pendle'
                    in_event = event

            elif event.asset == token_1 and event.amount == amount_1:
                if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE:  # noqa: E501
                    event.counterparty = CPT_PENDLE
                    event.event_type = HistoryEventType.RECEIVE
                    event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                    event.notes = f'Receive {amount_1} {token_1.symbol} from depositing into Pendle'  # noqa: E501
                    in_event = event
                elif event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE:  # noqa: E501
                    event.counterparty = CPT_PENDLE
                    event.event_type = HistoryEventType.SPEND
                    event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                    event.notes = f'Return {event.amount} {token_1.symbol} to Pendle'
                    out_event = event

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
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
        return DecodingOutput(action_items=action_items, process_swaps=True)

    def _decode_sy_pt_yt_events(
            self,
            context: DecoderContext,
            input_token_log_idx: int,
            output_token_log_idx: int,
            direction: Literal['mint', 'redeem', 'exit'],
    ) -> DecodingOutput:
        """Decodes Pendle SY/PT/YT mint, redeem, or post-expiry exit events"""
        amount_in = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[64:96]),
            asset=(token_in := self.base.get_token_or_native(bytes_to_address(context.tx_log.topics[input_token_log_idx]))),  # noqa: E501
        )
        amount_out = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[32:64]),
            asset=(token_out := self.base.get_token_or_native(token_out_address := bytes_to_address(context.tx_log.topics[output_token_log_idx]))),  # noqa: E501
        )
        out_events, in_events = [], []
        for event in context.decoded_events:
            if (
                    # Pendle emits one SPEND per output token (SY, PT, YT),
                    # each with the same amount.
                    event.amount == amount_out and
                    (event.address == token_out_address or event.asset == token_out) and
                    event.event_type in (HistoryEventType.SPEND, HistoryEventType.TRADE) and
                    event.event_subtype in (HistoryEventSubType.NONE, HistoryEventSubType.SPEND)
            ):
                out_events.append(event)
                event.counterparty = CPT_PENDLE
                if direction == 'mint':
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                    event.notes = f'Deposit {event.amount} {token_out.symbol} to Pendle'
                else:
                    event.event_type = HistoryEventType.SPEND
                    event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                    event.notes = f'Return {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} to Pendle'  # noqa: E501

            elif (
                    # Pendle emits one RECEIVE per output token (SY, PT, YT),
                    # each with the same amount.
                    event.amount == amount_in and
                    (event.address == ZERO_ADDRESS or event.asset == token_in) and
                    event.event_type in (HistoryEventType.RECEIVE, HistoryEventType.TRADE) and
                    event.event_subtype in (HistoryEventSubType.NONE, HistoryEventSubType.RECEIVE)
            ):
                in_events.append(event)
                event.counterparty = CPT_PENDLE
                if direction == 'mint':
                    event.event_type = HistoryEventType.RECEIVE
                    event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                    event.notes = f'Receive {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} from depositing into Pendle'  # noqa: E501
                else:
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                    if direction == 'exit':
                        event.notes = f'Withdraw {event.amount} {token_in.symbol} from a Pendle pool'  # noqa: E501
                    else:
                        event.notes = f'Withdraw {event.amount} {token_in.symbol} from Pendle'

        if len(in_events) == 0 or len(out_events) == 0:
            log.error(f'Could not retrieve either out events or in events in pendle {direction} transaction {context.transaction}')  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=out_events + in_events,
            events_list=context.decoded_events,
        )
        return DEFAULT_DECODING_OUTPUT

    def _decode_mint_sy_pt_yt_from_token(self, context: DecoderContext) -> DecodingOutput:
        """Decodes Pendle deposits where an underlying token is converted into SY, PT, or YT."""
        return self._decode_sy_pt_yt_events(
            context=context,
            direction='mint',
            input_token_log_idx=3,
            output_token_log_idx=2,
        )

    def _decode_redeem_sy_pt_yt_to_token(self, context: DecoderContext) -> DecodingOutput:
        """Decodes Pendle redemptions where SY, PT, or YT are converted back to the underlying token."""  # noqa: E501
        return self._decode_sy_pt_yt_events(
            context=context,
            direction='redeem',
            input_token_log_idx=2,
            output_token_log_idx=3,
        )

    def _decode_exit_post_exp_to_token(self, context: DecoderContext) -> DecodingOutput:
        """Decodes Pendle pool exits after maturity are redeemed for the underlying asset."""
        return self._decode_sy_pt_yt_events(
            context=context,
            direction='exit',
            input_token_log_idx=3,
            output_token_log_idx=2,
        )

    def _decode_claim_rewards(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != REDEEM_REWARDS_TOPIC:
            return DEFAULT_DECODING_OUTPUT

        raw_rewards_amount = int.from_bytes(context.tx_log.data[64:])
        for event in context.decoded_events:
            if (
                    event.address in self.pools and
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    asset_raw_value(
                        asset=(crypto_asset := event.asset.resolve_to_crypto_asset()),
                        amount=event.amount,
                    ) == raw_rewards_amount
            ):
                event.counterparty = CPT_PENDLE
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.REWARD
                event.notes = f'Claim {event.amount} {crypto_asset.symbol} reward from Pendle'
                break
        else:
            log.error(f'Could not find the pendle claim transfer for transaction {context.transaction}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_redeem_interests(self, context: DecoderContext) -> DecodingOutput:
        """Decode a Pendle redeem interests transaction."""
        if context.tx_log.topics[0] != REDEEM_TOPIC:
            return DEFAULT_DECODING_OUTPUT

        amount_in = asset_normalized_value(
            asset=(token_in := self.base.get_token_or_native(bytes_to_address(context.tx_log.topics[3]))),  # noqa: E501
            amount=int.from_bytes(context.tx_log.data[:32]),
        )
        amount_out = asset_normalized_value(
            asset=(token_out := self.base.get_or_create_evm_token(context.tx_log.address)),
            amount=int.from_bytes(context.tx_log.data[32:64]),
        )
        sy_in_event, sy_out_event = None, None
        for event in context.decoded_events:
            if event.asset == token_out and event.amount == amount_out:
                if (
                        event.event_type == HistoryEventType.RECEIVE and
                        event.event_subtype == HistoryEventSubType.NONE
                ):
                    sy_in_event = event

                elif (
                        event.event_type == HistoryEventType.SPEND and
                        event.event_subtype == HistoryEventSubType.NONE
                ):
                    sy_out_event = event

            elif (
                    event.asset == token_in and
                    event.amount == amount_in and
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE
            ):
                event.counterparty = CPT_PENDLE
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.notes = f'Withdraw {event.amount} {token_in.symbol} from Pendle'

        if not sy_in_event or not sy_out_event:
            log.error(f'Failed to in & out events of sy token for Pendle redeem interests transaction {context.transaction}')  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        # these SY receive/spend events cancel each other out, so we remove them.
        context.decoded_events.remove(sy_in_event)
        context.decoded_events.remove(sy_out_event)
        return DEFAULT_DECODING_OUTPUT

    def reload_data(self) -> Mapping['ChecksumEvmAddress', tuple[Any, ...]] | None:
        if should_update_protocol_cache(
                userdb=self.base.database,
                cache_key=CacheType.PENDLE_POOLS,
                args=(str(self.evm_inquirer.chain_id.serialize()),),
        ) or should_update_protocol_cache(
            userdb=self.base.database,
            cache_key=CacheType.PENDLE_SY_TOKENS,
            args=(str(self.evm_inquirer.chain_id.serialize()),),
        ):
            query_pendle_markets(self.evm_inquirer.chain_id)
        elif len(self.pools) != 0 and len(self.sy_tokens) == 0:
            return None  # we didn't update the globaldb cache, and we have the data already

        with GlobalDBHandler().conn.read_ctx() as cursor:
            self.pools = set(globaldb_get_general_cache_values(  # type: ignore[arg-type]  # addresses are always checksummed
                cursor=cursor,
                key_parts=(CacheType.PENDLE_POOLS, str(self.evm_inquirer.chain_id.serialize())),
            ))
            self.sy_tokens = set(globaldb_get_general_cache_values(  # type: ignore[arg-type]  # addresses are always checksummed
                cursor=cursor,
                key_parts=(CacheType.PENDLE_SY_TOKENS, str(self.evm_inquirer.chain_id.serialize())),  # noqa: E501
            ))

        return self.addresses_to_decoders()

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return ({
            PENDLE_ROUTER_ADDRESS: (self._decode_pendle_events,),
            PENDLE_SWAP_ADDRESS: (self._decode_pendle_swap,),
        } | dict.fromkeys(self.pools, (self._decode_claim_rewards,))
        | dict.fromkeys(self.sy_tokens, (self._decode_redeem_interests,)))

    @staticmethod
    def counterparties() -> tuple['CounterpartyDetails', ...]:
        return (CounterpartyDetails(
            identifier=CPT_PENDLE,
            label='Pendle Finance',
            image='pendle_light.svg',
            darkmode_image='pendle_dark.svg',
        ),)
