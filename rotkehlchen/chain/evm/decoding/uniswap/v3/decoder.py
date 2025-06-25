import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal, NamedTuple, Optional

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.utils import (
    CHAIN_TO_WRAPPED_TOKEN,
    TokenEncounterInfo,
    get_or_create_evm_token,
)
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    FAILED_ENRICHMENT_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.uniswap.utils import decode_basic_uniswap_info
from rotkehlchen.chain.evm.decoding.uniswap.v3.constants import (
    COLLECT_LIQUIDITY_SIGNATURE,
    INCREASE_LIQUIDITY_SIGNATURE,
    SWAP_SIGNATURE,
)
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog, SwapData
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.resolver import (
    evm_address_to_identifier,
    tokenid_belongs_to_collection,
    tokenid_to_collectible_id,
)
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    CHAINID_TO_SUPPORTED_BLOCKCHAIN,
    UNISWAPV3_PROTOCOL,
    ChecksumEvmAddress,
    EvmTransaction,
    TokenKind,
)
from rotkehlchen.utils.misc import ts_ms_to_sec

from ..constants import CPT_UNISWAP_V2, CPT_UNISWAP_V3, UNISWAP_ICON

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CryptoAssetAmount(NamedTuple):
    """This is used to represent a pair of resolved crypto asset to an amount."""
    asset: 'EvmToken'
    amount: FVal


def _find_from_asset_and_amount(events: list['EvmEvent']) -> tuple[Asset, FVal] | None:
    """
    Searches for uniswap v2/v3 swaps, detects `from_asset` and sums up `from_amount`.
    Works only with `from_asset` being the same for all swaps.
    """
    from_asset: Asset | None = None
    from_amount = ZERO
    for event in events:
        if (
            event.event_type == HistoryEventType.TRADE and
            event.event_subtype == HistoryEventSubType.SPEND and
            event.counterparty in {CPT_UNISWAP_V2, CPT_UNISWAP_V3}
        ):
            if from_asset is None:
                from_asset = event.asset
            elif from_asset != event.asset:  # We currently support only single `from_asset`.
                return None  # unexpected event

            from_amount += event.amount

    if from_asset is None:
        return None
    return from_asset, from_amount


class Uniswapv3CommonDecoder(DecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            routers_addresses: set['ChecksumEvmAddress'],
            nft_manager: 'ChecksumEvmAddress',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        chain = CHAINID_TO_SUPPORTED_BLOCKCHAIN[evm_inquirer.chain_id]
        self.native_currency = AssetResolver.resolve_asset(chain.get_native_token_id()).resolve_to_crypto_asset()  # noqa: E501
        self.wrapped_native_currency = CHAIN_TO_WRAPPED_TOKEN[chain]
        self.routers_addresses = routers_addresses
        self.nft_manager = nft_manager
        self.uniswap_v3_nft = evm_address_to_identifier(
            address=nft_manager,
            chain_id=evm_inquirer.chain_id,
            token_type=TokenKind.ERC721,
        )

    def _compare_with_maybe_native_token(
            self,
            event_asset: 'Asset',
            pool_token: 'EvmToken',
    ) -> tuple[bool, str]:
        """
        Compares an asset with a pool token, considering native currency equal to wrapped native
        currency. It returns a boolean if both are same and its symbol.
        """
        if pool_token == self.wrapped_native_currency and event_asset == self.native_currency:
            return True, event_asset.symbol_or_name()

        return event_asset == pool_token, pool_token.symbol

    def _find_to_asset_and_amount(self, events: list['EvmEvent']) -> tuple[Asset, FVal] | None:
        """
        Searches for uniswap v2/v3 swaps, detects `to_asset` and sums up `to_amount`.
        Works only with `to_asset` being the same for all swaps.
        Also works with a special case where there is only one receive event at the end.
        """
        to_asset: Asset | None = None
        to_amount = ZERO
        for event in events:
            if (
                event.event_type == HistoryEventType.TRADE and
                event.event_subtype == HistoryEventSubType.RECEIVE and
                event.counterparty in {CPT_UNISWAP_V2, CPT_UNISWAP_V3}
            ):
                # Some swaps have many receive events. The structure is:
                # spend1, receive1, spend2, receive2, ..., spendN, receiveN
                # In this case they will be decoded as trades and we check them here.
                if to_asset is None:
                    to_asset = event.asset
                elif to_asset != event.asset:  # We currently support only single `to_asset`.
                    return None  # unexpected event
                to_amount += event.amount
            elif event.event_type == HistoryEventType.RECEIVE and event.asset != self.native_currency and to_asset is None:  # noqa: E501
                # Some other swaps have only a single receive event. The structure is:
                # spend1, spend2, ..., spendN, receive
                # In this case the receive event won't be decoded as a trade and we check it here.
                # to_asset should be None here since it should be the only receive event.
                to_asset = event.asset
                to_amount = event.amount

        if to_asset is None:
            return None
        return to_asset, to_amount

    def _decode_deposits_and_withdrawals(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == INCREASE_LIQUIDITY_SIGNATURE:
            return self._maybe_decode_v3_deposit_or_withdrawal(
                context=context,
                event_action_type='addition',
            )
        if context.tx_log.topics[0] == COLLECT_LIQUIDITY_SIGNATURE:
            return self._maybe_decode_v3_deposit_or_withdrawal(
                context=context,
                event_action_type='removal',
            )

        return DEFAULT_DECODING_OUTPUT

    def _maybe_decode_v3_swap(
            self,
            token: EvmToken | None,  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list['EvmEvent'],
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> DecodingOutput:
        """
        Detect some basic uniswap v3 events. This method doesn't ensure the order of the events
        and other things, but just labels some of the events as uniswap v3 events.
        The order should be ensured by the post-decoding rules.
        """
        if tx_log.topics[0] != SWAP_SIGNATURE:
            return DEFAULT_DECODING_OUTPUT

        # Uniswap V3 represents the delta of tokens in the pool with a signed integer
        # for each token. In the transaction we have the difference of tokens in the pool
        # for the token0 [0:32] and the token1 [32:64]. If that difference is negative it
        # means that the tokens are leaving the pool (the user receives them) and if it is
        # positive they get into the pool (the user sends them to the pool)
        delta_token_0 = int.from_bytes(tx_log.data[0:32], signed=True)
        delta_token_1 = int.from_bytes(tx_log.data[32:64], signed=True)
        if delta_token_0 > 0:
            amount_sent, amount_received = delta_token_0, -delta_token_1
        else:
            amount_sent, amount_received = delta_token_1, -delta_token_0

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
            native_currency=self.native_currency,
        )

    # --- Routers methods ---

    def _decode_native_to_token_swap(
            self,
            decoded_events: list['EvmEvent'],
            send_native_event: 'EvmEvent',
            receive_native_event: Optional['EvmEvent'],
    ) -> SwapData | None:
        """
        Decode a swap of native currency to a token. Such swap consists of 3 events:
        1. Sending native currency to the router.
        2. If there is a refund, receiving native currency from the router.
        3. Receiving tokens from the router.
        """
        from_amount = send_native_event.amount
        if receive_native_event is not None:
            from_amount -= receive_native_event.amount  # a refund

        to_data = self._find_to_asset_and_amount(decoded_events)
        if to_data is None:
            return None

        return SwapData(
            from_asset=self.native_currency,
            from_amount=from_amount,
            to_asset=to_data[0],
            to_amount=to_data[1],
        )

    def _decode_token_to_native_swap(
            self,
            decoded_events: list['EvmEvent'],
            receive_native_event: 'EvmEvent',
    ) -> SwapData | None:
        from_data = _find_from_asset_and_amount(decoded_events)
        if from_data is None:
            return None

        return SwapData(
            from_asset=from_data[0],
            from_amount=from_data[1],
            to_asset=self.native_currency,
            to_amount=receive_native_event.amount,
        )

    def _decode_token_to_token_swap(
            self,
            decoded_events: list['EvmEvent'],
    ) -> SwapData | None:
        from_data = _find_from_asset_and_amount(decoded_events)
        to_data = self._find_to_asset_and_amount(decoded_events)
        if from_data is None or to_data is None:
            return None

        return SwapData(
            from_asset=from_data[0],
            from_amount=from_data[1],
            to_asset=to_data[0],
            to_amount=to_data[1],
        )

    def _routers_post_decoding(
            self,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> list['EvmEvent']:
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
        if len(decoded_events) < 3:
            # The minimum is 3 events: gas, spend, receive.
            return decoded_events

        send_native_event, receive_native_event = None, None
        for event in decoded_events:
            if event.asset == self.native_currency and event.counterparty != CPT_GAS:
                if event.event_type == HistoryEventType.SPEND:
                    send_native_event = event
                else:  # Receive
                    receive_native_event = event

        # Since we check that the to_address is a known router, we can be sure that the native
        # currency transfer event (and other events) are parts of the swap.
        if send_native_event is not None:
            # This is a swap from native to token
            # receive_native_event may be or may not be None depending on whether there was a refund  # noqa: E501
            swap_data = self._decode_native_to_token_swap(decoded_events, send_native_event, receive_native_event)  # noqa: E501
        elif receive_native_event is not None:
            # This is a swap from token to native
            swap_data = self._decode_token_to_native_swap(decoded_events, receive_native_event)
        else:
            # Then this should be a swap from token to token
            swap_data = self._decode_token_to_token_swap(decoded_events)

        if swap_data is None or swap_data.from_asset is None or swap_data.to_asset is None:
            log.error(f'Failed to decode a {self.evm_inquirer.chain_name} uniswap swap for transaction {transaction.tx_hash.hex()}')  # noqa: E501
            return decoded_events

        # These should never raise any errors since `from_asset` and `to_asset` are either native
        # currency or have already been resolved to tokens during erc20 transfers decoding.
        from_crypto_asset = swap_data.from_asset.resolve_to_crypto_asset()
        to_crypto_asset = swap_data.to_asset.resolve_to_crypto_asset()

        gas_event = None
        for event in decoded_events:
            if event.counterparty == CPT_GAS:
                gas_event = event
                break

        assert gas_event is not None, 'Gas event should always exist when interacting with a uniswap auto router'  # noqa: E501
        gas_event.sequence_index = 0

        timestamp = ts_ms_to_sec(decoded_events[0].timestamp)  # all events have same timestamp
        from_event = self.base.make_event(
            tx_hash=transaction.tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=from_crypto_asset,
            amount=swap_data.from_amount,
            location_label=transaction.from_address,
            notes=f'Swap {swap_data.from_amount} {from_crypto_asset.symbol} via {CPT_UNISWAP_V3} auto router',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
            address=transaction.to_address,
        )

        to_event = self.base.make_event(
            tx_hash=transaction.tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=to_crypto_asset,
            amount=swap_data.to_amount,
            location_label=transaction.from_address,
            notes=f'Receive {swap_data.to_amount} {to_crypto_asset.symbol} as the result of a swap via {CPT_UNISWAP_V3} auto router',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
            address=transaction.to_address,
        )

        return [gas_event, from_event, to_event]

    def _maybe_decode_v3_deposit_or_withdrawal(
            self,
            context: DecoderContext,
            event_action_type: Literal['addition', 'removal'],
    ) -> DecodingOutput:
        """
        This method decodes a Uniswap V3 LP liquidity increase or decrease.

        Examples of such transactions are:
        https://etherscan.io/tx/0x6bf3588f669a784adf5def3c0db149b0cdbcca775e472bb35f00acedee263c4c (deposit)
        https://etherscan.io/tx/0x76c312fe1c8604de5175c37dcbbb99cc8699336f3e4840e9e29e3383970f6c6d (withdrawal)
        """  # noqa: E501
        new_action_items = []
        liquidity_pool_id = int.from_bytes(context.tx_log.topics[1])
        amount0_raw = int.from_bytes(context.tx_log.data[32:64])
        amount1_raw = int.from_bytes(context.tx_log.data[64:96])

        if event_action_type == 'addition':
            notes = 'Deposit {amount} {asset} to uniswap-v3 LP {pool_id}'
            from_event_type = (HistoryEventType.SPEND, HistoryEventSubType.NONE)
            to_event_type = (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_FOR_WRAPPED)
        else:  # can only be 'removal'
            notes = 'Remove {amount} {asset} from uniswap-v3 LP {pool_id}'
            from_event_type = (HistoryEventType.RECEIVE, HistoryEventSubType.NONE)
            to_event_type = (HistoryEventType.WITHDRAWAL, HistoryEventSubType.REDEEM_WRAPPED)

        try:
            # Returns a tuple containing information about the state of the LP position.
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
            liquidity_pool_position_info = self.evm_inquirer.contracts.contract(self.nft_manager).call(  # noqa: E501
                node_inquirer=self.evm_inquirer,
                method_name='positions',
                arguments=[liquidity_pool_id],
            )
        except RemoteError:
            return DEFAULT_DECODING_OUTPUT

        resolved_assets_and_amounts: list[CryptoAssetAmount] = []
        # index 2 -> first token in pair; index 3 -> second token in pair
        for token, amount in zip(liquidity_pool_position_info[2:4], (amount0_raw, amount1_raw), strict=True):  # noqa: E501
            token_with_data = get_or_create_evm_token(
                userdb=self.evm_inquirer.database,
                evm_address=token,
                chain_id=self.evm_inquirer.chain_id,
                token_kind=TokenKind.ERC20,
                evm_inquirer=self.evm_inquirer,
                encounter=TokenEncounterInfo(tx_hash=context.transaction.tx_hash),
            )
            resolved_assets_and_amounts.append(CryptoAssetAmount(
                asset=token_with_data,
                amount=asset_normalized_value(amount, token_with_data),
            ))

        found_event_for_token0 = found_event_for_token1 = False
        for event in context.decoded_events:
            # search for the event of the first token
            token_0_matches_asset, maybe_event_asset_symbol = self._compare_with_maybe_native_token(  # noqa: E501
                event_asset=event.asset,
                pool_token=resolved_assets_and_amounts[0].asset,
            )
            if (
                token_0_matches_asset is True and
                event.amount == resolved_assets_and_amounts[0].amount and
                event.event_type == from_event_type[0] and
                event.event_subtype == from_event_type[1]
            ):
                found_event_for_token0 = True
                event.event_type = to_event_type[0]
                event.event_subtype = to_event_type[1]
                event.counterparty = CPT_UNISWAP_V3
                event.notes = notes.format(
                    amount=event.amount,
                    asset=maybe_event_asset_symbol,
                    pool_id=liquidity_pool_id,
                )
                continue

            # search for the event of the second token
            token_1_matches_asset, maybe_event_asset_symbol = self._compare_with_maybe_native_token(  # noqa: E501
                event_asset=event.asset,
                pool_token=resolved_assets_and_amounts[1].asset,
            )
            if (
                token_1_matches_asset is True and
                event.amount == resolved_assets_and_amounts[1].amount and
                event.event_type == from_event_type[0] and
                event.event_subtype == from_event_type[1]
            ):
                found_event_for_token1 = True
                event.event_type = to_event_type[0]
                event.event_subtype = to_event_type[1]
                event.counterparty = CPT_UNISWAP_V3
                event.notes = notes.format(
                    amount=event.amount,
                    asset=maybe_event_asset_symbol,
                    pool_id=liquidity_pool_id,
                )
                continue

        if found_event_for_token0 is False:
            new_action_items.append(
                ActionItem(
                    action='transform',
                    from_event_type=from_event_type[0],
                    from_event_subtype=from_event_type[1],
                    asset=resolved_assets_and_amounts[0].asset,
                    amount=resolved_assets_and_amounts[0].amount,
                    to_event_type=to_event_type[0],
                    to_event_subtype=to_event_type[1],
                    to_notes=notes.format(
                        amount=resolved_assets_and_amounts[0].amount,
                        asset=resolved_assets_and_amounts[0].asset.symbol,
                        pool_id=liquidity_pool_id,
                    ),
                    to_counterparty=CPT_UNISWAP_V3,
                ),
            )

        if found_event_for_token1 is False:
            new_action_items.append(
                ActionItem(
                    action='transform',
                    from_event_type=from_event_type[0],
                    from_event_subtype=from_event_type[1],
                    asset=resolved_assets_and_amounts[1].asset,
                    amount=resolved_assets_and_amounts[1].amount,
                    to_event_type=to_event_type[0],
                    to_event_subtype=to_event_type[1],
                    to_notes=notes.format(
                        amount=resolved_assets_and_amounts[1].amount,
                        asset=resolved_assets_and_amounts[1].asset.symbol,
                        pool_id=liquidity_pool_id,
                    ),
                    to_counterparty=CPT_UNISWAP_V3,
                ),
            )

        return DecodingOutput(action_items=new_action_items)

    def _maybe_enrich_liquidity_pool_creation(
            self,
            context: EnricherContext,
    ) -> TransferEnrichmentOutput:
        """This method enriches Uniswap V3 LP creation transactions and updates the
        position token's name and symbol to include the collectible id.
        """
        if (
            tokenid_belongs_to_collection(
                token_identifier=context.event.asset.identifier,
                collection_identifier=self.uniswap_v3_nft,
            ) and
            context.event.amount == ONE and
            context.event.address == ZERO_ADDRESS and
            context.event.event_type == HistoryEventType.RECEIVE and
            context.event.event_subtype == HistoryEventSubType.NONE
        ):
            context.event.event_type = HistoryEventType.DEPLOY
            context.event.event_subtype = HistoryEventSubType.NFT
            context.event.notes = f'Create {CPT_UNISWAP_V3} LP with id {int.from_bytes(context.tx_log.topics[3])}'  # noqa: E501
            context.event.counterparty = CPT_UNISWAP_V3
            context.event.asset = get_or_create_evm_token(
                userdb=self.evm_inquirer.database,
                evm_address=self.nft_manager,
                chain_id=self.evm_inquirer.chain_id,
                token_kind=TokenKind.ERC721,
                symbol=f'UNI-V3-POS-{(collectible_id := tokenid_to_collectible_id(identifier=context.event.asset.identifier))}',  # noqa: E501
                name=f'Uniswap V3 Positions #{collectible_id}',
                collectible_id=str(collectible_id),
                protocol=UNISWAPV3_PROTOCOL,
            )
            return TransferEnrichmentOutput(matched_counterparty=CPT_UNISWAP_V3)

        return FAILED_ENRICHMENT_OUTPUT

    # -- DecoderInterface methods

    def decoding_rules(self) -> list[Callable]:
        return [
            self._maybe_decode_v3_swap,
        ]

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            self.nft_manager: (self._decode_deposits_and_withdrawals,),
        }

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_liquidity_pool_creation,
        ]

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_UNISWAP_V3,
            label=CPT_UNISWAP_V3.capitalize().replace('-v', ' V'),
            image=UNISWAP_ICON,
        ),)

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_UNISWAP_V3: [(0, self._routers_post_decoding)]}

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return dict.fromkeys(self.routers_addresses, CPT_UNISWAP_V3)
