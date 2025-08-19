import logging
from collections import defaultdict
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import CHAIN_TO_WRAPPED_TOKEN
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, asset_raw_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V4, UNISWAP_ICON
from rotkehlchen.chain.evm.decoding.uniswap.utils import get_uniswap_swap_amounts
from rotkehlchen.chain.evm.decoding.uniswap.v3.constants import SWAP_SIGNATURE as V3_SWAP_TOPIC
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.constants.misc import ONE
from rotkehlchen.constants.resolver import evm_address_to_identifier, tokenid_to_collectible_id
from rotkehlchen.errors.asset import WrongAssetType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChecksumEvmAddress, TokenKind
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_UNISWAP_V4_LP, MODIFY_LIQUIDITY, POSITION_MANAGER_ABI, V4_SWAP_TOPIC

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import EvmTransaction
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Uniswapv4CommonDecoder(DecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
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

        if len(pool_info := self.evm_inquirer.call_contract(
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
            event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
            verb, from_to = 'Deposit', 'to'
        else:
            expected_type = HistoryEventType.RECEIVE
            event_type = HistoryEventType.WITHDRAWAL
            event_subtype = HistoryEventSubType.REDEEM_WRAPPED
            verb, from_to = 'Withdraw', 'from'

        # Edit the native currency event from the already decoded events, but use action items
        # to transform events for other tokens since they aren't present in decoded_events yet.
        if has_native:
            for event in context.decoded_events:
                if (
                        event.event_type == expected_type and
                        event.event_subtype == HistoryEventSubType.NONE and
                        event.asset == self.native_currency and
                        event.address == self.pool_manager
                ):
                    event.counterparty = CPT_UNISWAP_V4
                    event.event_type = event_type
                    event.event_subtype = event_subtype
                    event.notes = f'{verb} {event.amount} {self.native_currency.symbol} {from_to} {lp_str}'  # noqa: E501

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
        amounts_received, amounts_sent, pools_used, possible_fees = set(), set(), set(), defaultdict(list)  # noqa: E501
        # Since tokens may be swapped multiple times before reaching the desired token, we must
        # check the amounts from multiple swap logs if present.
        for tx_log in all_logs:
            if tx_log.topics[0] in (V4_SWAP_TOPIC, V3_SWAP_TOPIC):
                amount_received, amount_sent = get_uniswap_swap_amounts(tx_log=tx_log)
                amounts_received.add(amount_received)
                amounts_sent.add(amount_sent)
                pools_used.add(tx_log.address)
            elif (
                tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                ((from_addr := bytes_to_address(tx_log.topics[1])) == self.universal_router or
                from_addr in pools_used) and
                not self.base.is_tracked(bytes_to_address(tx_log.topics[2]))
            ):
                possible_fees[tx_log.address].append(int.from_bytes(tx_log.data[:32]))

        if len(amounts_received) == 0:
            log.error(f'Could not find Uniswap swap log in {transaction}')
            return decoded_events

        spend_event, receive_event, fee_event = None, None, None
        for event in decoded_events:
            if not (event.address == self.universal_router or event.address in pools_used):
                continue

            if (
                ((
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE
                ) or (
                    event.event_type == HistoryEventType.TRADE and
                    event.event_subtype == HistoryEventSubType.SPEND
                )) and
                asset_raw_value(
                    amount=event.amount,
                    asset=(resolved_asset := event.asset.resolve_to_crypto_asset()),
                ) in amounts_sent
            ):
                event.counterparty = CPT_UNISWAP_V4
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.notes = f'Swap {event.amount} {resolved_asset.symbol} in Uniswap V4'
                spend_event = event
            elif ((
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE
            ) or (
                event.event_type == HistoryEventType.TRADE and
                event.event_subtype == HistoryEventSubType.RECEIVE
            )):
                if (event_raw_amount := asset_raw_value(
                    amount=event.amount,
                    asset=(resolved_asset := event.asset.resolve_to_crypto_asset()),
                )) not in amounts_received:
                    # In some cases a fee is deducted from the receive amount before it is sent to
                    # the user. Check if this receive event actually has the right amount to match
                    # this swap after adding the fee back on.
                    try:  # First, get the received token's address
                        fee_token_address = (  # Fee will be in the wrapped version of the native currency.  # noqa: E501
                            event.asset if event.asset != self.native_currency
                            else self.wrapped_native_currency
                        ).resolve_to_evm_token().evm_address
                    except WrongAssetType:
                        log.error(
                            f'Uniswap V4 swap receive asset {event.asset} is not the native '
                            f'currency or an EVM token in {transaction}. Should not happen.')
                        continue

                    # Match against the amounts for possible fee transfers of this token
                    for amount in possible_fees[fee_token_address]:
                        if event_raw_amount + amount in amounts_received:
                            fee_amount = asset_normalized_value(
                                asset=resolved_asset,
                                amount=amount,
                            )
                            break
                    else:
                        continue  # this receive is not related to this swap

                    event.amount += fee_amount
                    fee_event = self.base.make_event_next_index(
                        tx_hash=event.tx_hash,
                        timestamp=transaction.timestamp,
                        event_type=HistoryEventType.TRADE,
                        event_subtype=HistoryEventSubType.FEE,
                        asset=resolved_asset,
                        amount=fee_amount,
                        location_label=event.location_label,
                        notes=f'Spend {fee_amount} {resolved_asset.symbol} as a Uniswap V4 fee',
                        counterparty=CPT_UNISWAP_V4,
                        address=event.address,
                    )

                event.counterparty = CPT_UNISWAP_V4
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {event.amount} {resolved_asset.symbol} after a swap in Uniswap V4'  # noqa: E501
                receive_event = event

        if spend_event is None or receive_event is None:
            log.error(f'Failed to find both out and in events for Uniswap V4 swap {transaction}')
            return decoded_events

        ordered_events = [spend_event, receive_event]
        if fee_event is not None:
            decoded_events.append(fee_event)
            ordered_events.append(fee_event)

        maybe_reshuffle_events(ordered_events=ordered_events, events_list=decoded_events)
        return decoded_events

    def _lp_post_decoding(
            self,
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        """Decode LP position NFT mint/burn events and properly reshuffle them along with
        the deposit/withdraw events already decoded by _decode_modify_liquidity.
        """
        deposit_withdrawal_events, mint_events, burn_events = [], [], []
        for event in decoded_events:
            if (
                event.event_type in (HistoryEventType.SPEND, HistoryEventType.RECEIVE) and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == ZERO_ADDRESS and
                event.amount == ONE and
                (collectible_id := tokenid_to_collectible_id(
                    identifier=event.asset.identifier,
                )) is not None and
                event.asset == Asset(evm_address_to_identifier(
                    address=self.position_manager,
                    chain_id=self.evm_inquirer.chain_id,
                    token_type=TokenKind.ERC721,
                    collectible_id=collectible_id,
                ))
            ):
                if event.event_type == HistoryEventType.SPEND:
                    event.event_type = HistoryEventType.BURN
                    verb = 'Exit'
                    burn_events.append(event)
                else:  # HistoryEventType.RECEIVE
                    event.event_type = HistoryEventType.DEPLOY
                    verb = 'Create'
                    mint_events.append(event)

                event.counterparty = CPT_UNISWAP_V4
                event.event_subtype = HistoryEventSubType.NFT
                event.notes = f'{verb} Uniswap V4 LP with id {collectible_id}'
            elif (
                event.counterparty == CPT_UNISWAP_V4 and
                ((
                    event.event_type == HistoryEventType.DEPOSIT and
                    event.event_subtype == HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                ) or (
                    event.event_type == HistoryEventType.WITHDRAWAL and
                    event.event_subtype == HistoryEventSubType.REDEEM_WRAPPED
                ))
            ):
                deposit_withdrawal_events.append(event)

        maybe_reshuffle_events(
            ordered_events=burn_events + deposit_withdrawal_events + mint_events,
            events_list=decoded_events,
        )
        return decoded_events

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
