import logging
from collections import defaultdict
from collections.abc import Callable
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import CHAIN_TO_WRAPPED_TOKEN
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, asset_raw_value
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V4, UNISWAP_ICON
from rotkehlchen.chain.evm.decoding.uniswap.utils import get_uniswap_swap_amounts
from rotkehlchen.chain.evm.decoding.uniswap.v3.constants import SWAP_SIGNATURE as V3_SWAP_TOPIC
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.errors.asset import WrongAssetType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import V4_SWAP_TOPIC

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
        self.universal_router = universal_router

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

    # -- DecoderInterface methods

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_UNISWAP_V4: [(0, self._router_post_decoding)]}

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return {self.universal_router: CPT_UNISWAP_V4}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails.from_versioned_counterparty(
            counterparty=CPT_UNISWAP_V4,
            image=UNISWAP_ICON,
        ),)
