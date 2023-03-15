import logging
from typing import TYPE_CHECKING, Any, Callable, Optional

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.ethereum.modules.cowswap.constants import CPT_COWSWAP
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import ActionItem
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog, SwapData
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_WETH
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTokenKind, EvmTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

TRADE_SIGNATURE = b'\xa0zT:\xb8\xa0\x18\x19\x8e\x99\xca\x01\x84\xc9?\xe9\x05\ny@\n\nr4A\xf8M\xe1\xd9r\xcc\x17'  # noqa: E501
PLACE_ETH_ORDER_SIGNATURE = b"\xcf_\x9d\xe2\x98A2&R\x03\xb5\xc35\xb2W\'p,\xa7rb\xffb.\x13k\xaasb\xbf\x1d\xa9"  # noqa: E501
REFUND_ETH_ORDER_SIGNATURE = b'\x19Rq\x06\x8a(\x81\x91\xe4\xb2e\xc6A\xa5k\x982\x91\x9fi\xe9\xe7\xd6\xc2\xf3\x1b\xa4\x02x\xae\xb8Z'  # noqa: E501
INVALIDATE_ETH_ORDER_SIGNATURE = b'\xb8\xba\xd1\x02\xac\x8b\xba\xcf\xef1\xff\x1c\x90n\xc6\xd9Q\xc20\xb4\xdc\xe7P\xbb\x03v\xb8\x12\xad5\x85*'  # noqa: E501

GPV2_SETTLEMENT_ADDRESS = string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41')
ETH_FLOW_ADDRESS = string_to_evm_address('0x40A50cf069e992AA4536211B23F286eF88752187')


class CowswapDecoder(DecoderInterface):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.eth = A_ETH.resolve_to_crypto_asset()

    def _decode_eth_orders(
            self,
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list[EvmEvent],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
            action_items: list[ActionItem],  # pylint: disable=unused-argument
    ) -> tuple[Optional[EvmEvent], list[ActionItem]]:
        if tx_log.topics[0] == PLACE_ETH_ORDER_SIGNATURE:
            target_token_address = hex_or_bytes_to_address(tx_log.data[32:64])
            target_token = EvmToken(evm_address_to_identifier(
                address=target_token_address,
                chain_id=ChainID.ETHEREUM,
                token_type=EvmTokenKind.ERC20,
            ))
            for event in decoded_events:
                if (
                    event.event_type == HistoryEventType.SPEND and
                    event.asset == A_ETH and
                    event.address == ETH_FLOW_ADDRESS
                ):
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.PLACE_ORDER
                    event.notes = f'Deposit {event.balance.amount} ETH to swap it for {target_token.symbol} in cowswap'  # noqa: E501
                    event.counterparty = CPT_COWSWAP

        elif tx_log.topics[0] in (INVALIDATE_ETH_ORDER_SIGNATURE, REFUND_ETH_ORDER_SIGNATURE):
            for event in decoded_events:
                if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.asset == A_ETH and
                    event.address == ETH_FLOW_ADDRESS
                ):
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.counterparty = CPT_COWSWAP
                    if tx_log.topics[0] == INVALIDATE_ETH_ORDER_SIGNATURE:
                        event.event_subtype = HistoryEventSubType.CANCEL_ORDER
                        event.notes = f'Invalidate an order that intended to swap {event.balance.amount} ETH in cowswap'  # noqa: E501
                    else:  # Refund
                        event.event_subtype = HistoryEventSubType.REFUND
                        event.notes = f'Refund {event.balance.amount} unused ETH from cowswap'

        return None, []

    # --- Aggregator methods ---

    def _find_trades(self, all_logs: list[EvmTxReceiptLog]) -> list[SwapData]:
        """
        Finds the emitted Trade events and decodes them.
        Also handles special cases when ETH is swapped.

        Returns a list of swap data. Each entry in the list contains basic information about a
        swap made in the transaction.
        """
        trades = []

        for tx_log in all_logs:
            if tx_log.topics[0] != TRADE_SIGNATURE:
                continue

            owner_address = hex_or_bytes_to_address(tx_log.topics[1])
            from_token_address = hex_or_bytes_to_address(tx_log.data[:32])
            to_token_address = hex_or_bytes_to_address(tx_log.data[32:64])
            raw_from_amount = hex_or_bytes_to_int(tx_log.data[64:96])
            raw_to_amount = hex_or_bytes_to_int(tx_log.data[96:128])

            if (
                from_token_address == A_WETH.resolve_to_evm_token().evm_address and
                owner_address == ETH_FLOW_ADDRESS
            ):
                from_asset = self.eth  # ETH swaps are made by eth flow contract in cowswap
            else:  # token should exist since this is the post-processing stage
                from_asset = EvmToken(evm_address_to_identifier(
                    address=from_token_address,
                    chain_id=ChainID.ETHEREUM,
                    token_type=EvmTokenKind.ERC20,
                ))
            to_asset = self.eth if to_token_address == ETH_SPECIAL_ADDRESS else EvmToken(
                evm_address_to_identifier(  # token should exist since this is the post-processing stage  # noqa: E501
                    address=to_token_address,
                    chain_id=ChainID.ETHEREUM,
                    token_type=EvmTokenKind.ERC20,
                ),
            )
            from_amount = asset_normalized_value(amount=raw_from_amount, asset=from_asset)
            to_amount = asset_normalized_value(amount=raw_to_amount, asset=to_asset)

            trades.append(SwapData(
                from_asset=from_asset,
                from_amount=from_amount,
                to_asset=to_asset,
                to_amount=to_amount,
            ))

        return trades

    def _detect_relevant_trades(
            self,
            transaction: EvmTransaction,
            all_swap_data: list[SwapData],
            decoded_events: list[EvmEvent],
    ) -> list[tuple[EvmEvent, EvmEvent]]:
        """
        This function does the following
        1. Detect trades that are relevant to the tracked accounts.
        2. For each trade, find the corresponding spend event and receive event. For swaps where
        ETH is spent creates a new ETH spend event.

        Each relevant trade has an optional spend event (since sometimes ETH is spent,
        and in these cases there is no spend event) and a mandatory receive event, so to detect
        relevant trades we check which trades have a decoded eth/token receive event.

        Returns a list of pairs (spend_event, receive_event) which represent the relevant trades.
        """
        related_transfer_events: dict[tuple[HistoryEventType, Asset, FVal], EvmEvent] = {}
        for event in decoded_events:
            if (
                event.event_type in (HistoryEventType.SPEND, HistoryEventType.RECEIVE) and
                event.address == GPV2_SETTLEMENT_ADDRESS
            ):
                related_transfer_events[(event.event_type, event.asset, event.balance.amount)] = event  # noqa: E501

        trades_events: list[tuple[EvmEvent, EvmEvent]] = []
        for swap_data in all_swap_data:
            receive_event = related_transfer_events.get((HistoryEventType.RECEIVE, swap_data.to_asset, swap_data.to_amount))  # noqa: E501
            if receive_event is None:
                continue

            if swap_data.from_asset != A_ETH:
                # If a token is spent, there has to be an event for that.
                spend_event = related_transfer_events.get((HistoryEventType.SPEND, swap_data.from_asset, swap_data.from_amount))  # noqa: E501
                if spend_event is None:
                    log.error(
                        f'Could not find a spend event of {swap_data.from_amount} '
                        f'{swap_data.from_asset} in a cowswap transaction {transaction.tx_hash.hex()}')  # noqa: E501
                    continue
            else:
                # If ETH is spent, then there will not be a decoded transfer. Thus we create it.
                spend_event = self.base.make_event_next_index(
                    tx_hash=transaction.tx_hash,
                    timestamp=transaction.timestamp,
                    event_type=HistoryEventType.SPEND,  # Is customized later
                    event_subtype=HistoryEventSubType.NONE,
                    asset=swap_data.from_asset,
                    balance=Balance(amount=swap_data.from_amount),
                    location_label=receive_event.location_label,
                    notes=None,  # Is set later
                    counterparty=CPT_COWSWAP,
                    address=transaction.to_address,
                )
                decoded_events.append(spend_event)

            trades_events.append((spend_event, receive_event))

        return trades_events

    def _aggregator_post_decoding(
            self,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            all_logs: list[EvmTxReceiptLog],
    ) -> list[EvmEvent]:
        """
        Decodes cowswap trades.
        1. Goes through all the emitted Trade events.
        2. Filters out trades that are not relevant to the tracked accounts.
        3. For each trade finds or generates if missing spend and receive events.
        4. Makes sure that spend-receive pairs are consecutive.
        """
        if transaction.to_address != GPV2_SETTLEMENT_ADDRESS:
            return decoded_events

        all_swap_data = self._find_trades(all_logs)
        relevant_trades = self._detect_relevant_trades(
            transaction=transaction,
            all_swap_data=all_swap_data,
            decoded_events=decoded_events,
        )
        for spend_event, receive_event in relevant_trades:
            spend_event.counterparty = CPT_COWSWAP
            receive_event.counterparty = CPT_COWSWAP
            spend_event.event_type = HistoryEventType.TRADE
            receive_event.event_type = HistoryEventType.TRADE
            spend_event.event_subtype = HistoryEventSubType.SPEND
            receive_event.event_subtype = HistoryEventSubType.RECEIVE
            spend_event.notes = f'Swap {spend_event.balance.amount} {spend_event.asset.symbol_or_name()} in cowswap'  # noqa: E501
            receive_event.notes = f'Receive {receive_event.balance.amount} {receive_event.asset.symbol_or_name()} as the result of a swap in cowswap'  # noqa: E501
            maybe_reshuffle_events(out_event=spend_event, in_event=receive_event, events_list=decoded_events)  # noqa: E501

        return decoded_events

    # -- DecoderInterface methods

    def counterparties(self) -> list[str]:
        return [CPT_COWSWAP]

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {ETH_FLOW_ADDRESS: (self._decode_eth_orders,)}

    def post_decoding_rules(self) -> list[tuple[int, Callable]]:
        return [(0, self._aggregator_post_decoding)]
