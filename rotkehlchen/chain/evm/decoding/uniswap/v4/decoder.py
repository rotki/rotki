import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import CHAIN_TO_WRAPPED_TOKEN
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V4, UNISWAP_ICON
from rotkehlchen.chain.evm.decoding.uniswap.utils import (
    decode_uniswap_v3_like_position_create_or_exit,
)
from rotkehlchen.chain.evm.decoding.uniswap.v3.constants import SWAP_SIGNATURE as V3_SWAP_TOPIC
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChecksumEvmAddress

from .constants import CPT_UNISWAP_V4_LP, MODIFY_LIQUIDITY, POSITION_MANAGER_ABI, V4_SWAP_TOPIC
from .utils import decode_uniswap_v4_like_swaps

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import EvmTransaction
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Uniswapv4CommonDecoder(EvmDecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            pool_manager: 'ChecksumEvmAddress',
            position_manager: 'ChecksumEvmAddress',
            universal_router: 'ChecksumEvmAddress',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.native_currency = Asset(
            identifier=evm_inquirer.blockchain.get_native_token_id(),
        ).resolve_to_crypto_asset()
        self.wrapped_native_currency = CHAIN_TO_WRAPPED_TOKEN[evm_inquirer.blockchain]
        self.pool_manager = pool_manager
        self.position_manager = position_manager
        self.universal_router = universal_router

    def _decode_modify_liquidity(self, context: 'DecoderContext') -> 'DecodingOutput':
        if context.tx_log.topics[0] != MODIFY_LIQUIDITY:
            return DEFAULT_DECODING_OUTPUT

        if len(pool_info := self.node_inquirer.call_contract(
            contract_address=self.position_manager,
            abi=POSITION_MANAGER_ABI,
            method_name='poolKeys',
            arguments=[context.tx_log.topics[1][:25]],
        )) != 5:
            log.error(f'Unexpected response from Uniswap V4 Position Manager poolKeys call: {pool_info}')  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        lp_assets, has_native = [], False
        for raw_address in pool_info[:2]:
            if (asset_address := deserialize_evm_address(raw_address)) == ZERO_ADDRESS:
                lp_assets.append(self.native_currency)
                has_native = True
            else:
                lp_assets.append(self.base.get_or_create_evm_token(asset_address))

        lp_str = f'Uniswap V4 {"/".join(x.symbol for x in lp_assets)} LP'
        # positive/negative liquidity delta indicates if it's a deposit/withdrawal.
        if int.from_bytes(context.tx_log.data[64:96], signed=True) > 0:
            expected_type = HistoryEventType.SPEND
            event_type = HistoryEventType.DEPOSIT
            event_subtype = HistoryEventSubType.DEPOSIT_ASSET
            verb, from_to = 'Deposit', 'to'
        else:
            expected_type = HistoryEventType.RECEIVE
            event_type = HistoryEventType.WITHDRAWAL
            event_subtype = HistoryEventSubType.REMOVE_ASSET
            verb, from_to = 'Withdraw', 'from'

        # Edit the native currency event from the already decoded events, but use action items
        # to transform events for other tokens since they aren't present in decoded_events yet.
        if has_native:
            refund_event, deposit_withdraw_event = None, None
            for event in context.decoded_events:
                if (
                        event.event_subtype == HistoryEventSubType.NONE and
                        event.asset == self.native_currency and
                        event.address in (self.pool_manager, self.position_manager)
                ):
                    if event.event_type == expected_type:
                        event.counterparty = CPT_UNISWAP_V4
                        event.event_type = event_type
                        event.event_subtype = event_subtype
                        event.notes = f'{verb} {{amount}} {self.native_currency.symbol} {from_to} {lp_str}'  # noqa: E501
                        deposit_withdraw_event = event
                    elif (
                        expected_type == HistoryEventType.SPEND and
                        event.event_type == HistoryEventType.RECEIVE
                    ):
                        # Unlike approved tokens where the contract requests an exact amount,
                        # the approximate amount of the native asset sent may require a refund.
                        refund_event = event

            if deposit_withdraw_event is not None:
                if refund_event is not None:
                    deposit_withdraw_event.amount -= refund_event.amount
                    context.decoded_events.remove(refund_event)

                deposit_withdraw_event.notes = deposit_withdraw_event.notes.format(  # type: ignore  # notes will not be None
                    amount=deposit_withdraw_event.amount,
                )

        return DecodingOutput(
            matched_counterparty=CPT_UNISWAP_V4_LP,  # Trigger _lp_post_decoding
            action_items=[ActionItem(
                action='transform',
                from_event_type=expected_type,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=asset,
                address=self.pool_manager,
                to_event_type=event_type,
                to_event_subtype=event_subtype,
                to_notes=f'{verb} {{amount}} {asset.symbol} {from_to} {lp_str}',  # amount is set when the action item is processed  # noqa: E501
                to_counterparty=CPT_UNISWAP_V4,
            ) for asset in (x for x in lp_assets if x != self.native_currency)],
        )

    def _router_post_decoding(
            self,
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        """Decode swaps routed through the Uniswap V4 universal router."""
        return decode_uniswap_v4_like_swaps(
            transaction=transaction,
            decoded_events=decoded_events,
            all_logs=all_logs,
            base_tools=self.base,
            swap_topics=(V4_SWAP_TOPIC, V3_SWAP_TOPIC),
            counterparty=CPT_UNISWAP_V4,
            router_address=self.universal_router,
            wrapped_native_currency=self.wrapped_native_currency,
        )

    def _lp_post_decoding(
            self,
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        """Decode LP position NFT mint/burn events and properly reshuffle them along with
        the deposit/withdraw events already decoded by _decode_modify_liquidity.
        """
        return decode_uniswap_v3_like_position_create_or_exit(
            decoded_events=decoded_events,
            evm_inquirer=self.node_inquirer,
            nft_manager=self.position_manager,
            counterparty=CPT_UNISWAP_V4,
            token_symbol='UNI-V4-POS',
            token_name='Uniswap V4 Positions',
        )

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return {self.pool_manager: (self._decode_modify_liquidity,)}

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {
            CPT_UNISWAP_V4: [(0, self._router_post_decoding)],
            CPT_UNISWAP_V4_LP: [(0, self._lp_post_decoding)],
        }

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return {self.universal_router: CPT_UNISWAP_V4}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails.from_versioned_counterparty(
            counterparty=CPT_UNISWAP_V4,
            image=UNISWAP_ICON,
        ),)
