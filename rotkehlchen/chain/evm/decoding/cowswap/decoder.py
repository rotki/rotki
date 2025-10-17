import abc
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final, Literal, Optional, cast

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.utils import TokenEncounterInfo
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, token_normalized_value
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS
from rotkehlchen.chain.evm.decoding.airdrops import match_airdrop_claim
from rotkehlchen.chain.evm.decoding.cowswap.constants import COWSWAP_CPT_DETAILS, CPT_COWSWAP
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.cowswap import SUPPORTED_COWSWAP_BLOCKCHAIN, CowswapAPI
from rotkehlchen.history.events.structures.types import (
    EventDirection,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTransaction, EVMTxHash, TokenKind
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.binance_sc.node_inquirer import BinanceSCInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

TRADE_SIGNATURE: Final = b'\xa0zT:\xb8\xa0\x18\x19\x8e\x99\xca\x01\x84\xc9?\xe9\x05\ny@\n\nr4A\xf8M\xe1\xd9r\xcc\x17'  # noqa: E501
PLACE_NATIVE_ASSET_ORDER_SIGNATURE: Final = b"\xcf_\x9d\xe2\x98A2&R\x03\xb5\xc35\xb2W'p,\xa7rb\xffb.\x13k\xaasb\xbf\x1d\xa9"  # noqa: E501
REFUND_NATIVE_ASSET_ORDER_SIGNATURE: Final = b'\x19Rq\x06\x8a(\x81\x91\xe4\xb2e\xc6A\xa5k\x982\x91\x9fi\xe9\xe7\xd6\xc2\xf3\x1b\xa4\x02x\xae\xb8Z'  # noqa: E501
INVALIDATE_NATIVE_ASSET_ORDER_SIGNATURE: Final = b'\xb8\xba\xd1\x02\xac\x8b\xba\xcf\xef1\xff\x1c\x90n\xc6\xd9Q\xc20\xb4\xdc\xe7P\xbb\x03v\xb8\x12\xad5\x85*'  # noqa: E501
VESTED: Final = b'\x00\xd5\x95\x87\x99\xb1\x83\xa7\xb78\xd3\xad^q\x13\x05)=\xd5\x07j7\xa4\xe3\xb7\xe6a\x1d\xeaa\x14\xf3'  # noqa: E501

GPV2_SETTLEMENT_ADDRESS: Final = string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41')  # noqa: E501
NATIVE_ASSET_FLOW_ADDRESSES: Final = (
    string_to_evm_address('0x40A50cf069e992AA4536211B23F286eF88752187'),
    string_to_evm_address('0xbA3cB449bD2B4ADddBc894D8697F5170800EAdeC'),
)
CLAIMED: Final = b'\xd46\xe9\x97=\x1eD\xd4\r\xb4\xd4\x11\x9e<w<\xad\xb12;&9\x81\x96\x8c\x14\xd3\xd1\x91\xc0\xe1H'  # noqa: E501


@dataclass
class CowswapSwapData:
    """Data class that holds information about a cowswap swap"""
    from_asset: Asset
    from_amount: 'FVal'
    to_asset: Asset
    to_amount: 'FVal'
    fee_amount: 'FVal'
    order_uid: str  # a hexstring without the 0x prefix
    order_type: str = 'market'


class CowswapCommonDecoder(EvmDecoderInterface, abc.ABC):

    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer | ArbitrumOneInquirer | GnosisInquirer | BaseInquirer | BinanceSCInquirer',  # noqa: E501
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            native_asset: Asset,
            wrapped_native_asset: Asset,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.native_asset = native_asset.resolve_to_crypto_asset()
        self.wrapped_native_asset = wrapped_native_asset.resolve_to_evm_token()
        self.settlement_address = GPV2_SETTLEMENT_ADDRESS
        self.native_asset_flow_addresses = NATIVE_ASSET_FLOW_ADDRESSES
        self.cowswap_api = CowswapAPI(
            database=self.node_inquirer.database,
            chain=cast('SUPPORTED_COWSWAP_BLOCKCHAIN', self.node_inquirer.blockchain),
        )

    def _decode_native_asset_orders(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == PLACE_NATIVE_ASSET_ORDER_SIGNATURE:
            target_token_address = bytes_to_address(context.tx_log.data[32:64])
            target_token = EvmToken(evm_address_to_identifier(
                address=target_token_address,
                chain_id=self.node_inquirer.chain_id,
                token_type=TokenKind.ERC20,
            ))
            for event in context.decoded_events:
                if (
                    event.event_type == HistoryEventType.SPEND and
                    event.asset == self.native_asset and
                    event.address in self.native_asset_flow_addresses
                ):
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.PLACE_ORDER
                    event.notes = f'Deposit {event.amount} {self.native_asset.symbol} to swap it for {target_token.symbol} in cowswap'  # noqa: E501
                    event.counterparty = CPT_COWSWAP

        elif context.tx_log.topics[0] in (INVALIDATE_NATIVE_ASSET_ORDER_SIGNATURE, REFUND_NATIVE_ASSET_ORDER_SIGNATURE):  # noqa: E501
            for event in context.decoded_events:
                if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.asset == self.native_asset and
                    event.address in self.native_asset_flow_addresses
                ):
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.counterparty = CPT_COWSWAP
                    if context.tx_log.topics[0] == INVALIDATE_NATIVE_ASSET_ORDER_SIGNATURE:
                        event.event_subtype = HistoryEventSubType.CANCEL_ORDER
                        event.notes = f'Invalidate an order that intended to swap {event.amount} {self.native_asset.symbol} in cowswap'  # noqa: E501
                    else:  # Refund
                        event.event_subtype = HistoryEventSubType.REFUND
                        event.notes = f'Refund {event.amount} unused {self.native_asset.symbol} from cowswap'  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    # --- Aggregator methods ---

    def _find_trades(
            self,
            tx_hash: EVMTxHash,
            all_logs: list[EvmTxReceiptLog],
    ) -> list[CowswapSwapData]:
        """
        Finds the emitted Trade events and decodes them.
        Also handles special cases when native asset is swapped.

        Returns a list of swap data. Each entry in the list contains basic information about a
        swap made in the transaction.
        """
        trades, tx_info = [], TokenEncounterInfo(tx_ref=tx_hash, description='CowSwap trade')
        for tx_log in all_logs:
            if tx_log.topics[0] != TRADE_SIGNATURE:
                continue

            owner_address = bytes_to_address(tx_log.topics[1])
            from_token_address = bytes_to_address(tx_log.data[:32])
            to_token_address = bytes_to_address(tx_log.data[32:64])
            raw_from_amount = int.from_bytes(tx_log.data[64:96])
            raw_to_amount = int.from_bytes(tx_log.data[96:128])
            raw_fee_amount = int.from_bytes(tx_log.data[128:160])
            order_uid = tx_log.data[224:280].hex()

            if (
                from_token_address == self.wrapped_native_asset.evm_address and
                owner_address in self.native_asset_flow_addresses
            ):
                from_asset = self.native_asset  # native asset swaps are made by eth flow contract in cowswap  # noqa: E501
            else:  # need get_or_create_evm_token because token may not exist if there was a remote error the first time that the token appeared.  # noqa: E501
                from_asset = self.base.get_or_create_evm_token(
                    address=from_token_address,
                    encounter=tx_info,
                )
            to_asset = self.native_asset if to_token_address == ETH_SPECIAL_ADDRESS else self.base.get_or_create_evm_token(  # noqa: E501
                address=to_token_address,
                encounter=tx_info,
            )
            fee_amount = asset_normalized_value(amount=raw_fee_amount, asset=from_asset)
            from_amount = asset_normalized_value(amount=raw_from_amount, asset=from_asset)
            to_amount = asset_normalized_value(amount=raw_to_amount, asset=to_asset)

            trades.append(CowswapSwapData(
                from_asset=self.base.exceptions_mappings.get(from_asset.identifier, from_asset).resolve_to_crypto_asset(),  # noqa: E501
                from_amount=from_amount - fee_amount,  # fee is taken as part of from asset
                to_asset=self.base.exceptions_mappings.get(to_asset.identifier, to_asset).resolve_to_crypto_asset(),  # noqa: E501
                to_amount=to_amount,
                fee_amount=fee_amount,
                order_uid=order_uid,
            ))

        return trades

    def _detect_relevant_trades(
            self,
            transaction: EvmTransaction,
            all_swap_data: list[CowswapSwapData],
            decoded_events: list['EvmEvent'],
    ) -> list[tuple['EvmEvent', 'EvmEvent', Optional['EvmEvent'], CowswapSwapData]]:
        """
        This function does the following
        1. Detect trades that are relevant to the tracked accounts.
        2. For each trade, find the corresponding spend event and receive event. For swaps where
        native asset is spent creates a new native asset spend event.
        3. Create a fee event, using either the onchain fee data, or by querying the cowswap API.

        Each relevant trade has an optional spend event (since sometimes native asset is spent,
        and in these cases there is no spend event) and a mandatory receive event, so to detect
        relevant trades we check which trades have a decoded native_asset/token receive event.

        Returns a list of pairs (spend_event, receive_event, fee_event, swap_data)
        which represent the relevant trades.
        """
        related_transfer_events: dict[tuple[EventDirection, Asset, FVal], EvmEvent] = {}
        for event in decoded_events:
            if (
                    (event.event_type in (HistoryEventType.SPEND, HistoryEventType.RECEIVE) or
                     (event.event_type == HistoryEventType.TRADE and event.event_subtype in (HistoryEventSubType.SPEND, HistoryEventSubType.RECEIVE))  # noqa: E501
                     ) and
                    event.address == self.settlement_address
            ):
                direction = event.maybe_get_direction()
                if direction is None:
                    log.error(f'Could not find direction of event {event}. Should never happen')
                    continue

                related_transfer_events[direction, event.asset, event.amount] = event

        trades_events: list[tuple[EvmEvent, EvmEvent, EvmEvent | None, CowswapSwapData]] = []
        for swap_data in all_swap_data:
            receive_event = related_transfer_events.get((EventDirection.IN, swap_data.to_asset, swap_data.to_amount))  # noqa: E501
            if receive_event is None:
                continue

            if swap_data.from_asset != self.native_asset:
                # If a token is spent, there has to be an event for that.
                spend_event = related_transfer_events.get((EventDirection.OUT, swap_data.from_asset, swap_data.from_amount + swap_data.fee_amount))  # noqa: E501
                if spend_event is None:
                    log.error(
                        f'Could not find a spend event of {swap_data.from_amount} '
                        f'{swap_data.from_asset} in a {self.node_inquirer.chain_name} cowswap transaction {transaction.tx_hash.hex()}')  # noqa: E501
                    continue
            else:
                # If native asset is spent, then there will not be a decoded transfer. Thus we create it.  # noqa: E501
                spend_event = self.base.make_event_next_index(
                    tx_ref=transaction.tx_hash,
                    timestamp=transaction.timestamp,
                    event_type=HistoryEventType.SPEND,  # Is customized later
                    event_subtype=HistoryEventSubType.NONE,
                    asset=swap_data.from_asset,
                    amount=swap_data.from_amount,
                    location_label=receive_event.location_label,
                    notes=None,  # Is set later
                    counterparty=CPT_COWSWAP,
                    address=transaction.to_address,
                )
                decoded_events.append(spend_event)

            if swap_data.fee_amount == ZERO:
                try:
                    raw_fee_amount, swap_data.order_type = self.cowswap_api.get_order_data(swap_data.order_uid)  # noqa: E501
                except RemoteError as e:
                    log.error(f'Failed to get fee and order type from cowswap API for transaction {transaction} due to {e!s}. Will proceed without them.')  # noqa: E501
                    raw_fee_amount = 0

                swap_data.fee_amount = asset_normalized_value(
                    amount=raw_fee_amount,
                    asset=swap_data.from_asset.resolve_to_crypto_asset(),
                )
                swap_data.from_amount -= swap_data.fee_amount  # fee is taken as part of from asset

            fee_event = None
            if swap_data.fee_amount != ZERO:
                fee_event = self.base.make_event_next_index(
                    tx_ref=transaction.tx_hash,
                    timestamp=transaction.timestamp,
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.FEE,
                    asset=swap_data.from_asset,
                    amount=swap_data.fee_amount,
                    notes=f'Spend {swap_data.fee_amount} {swap_data.from_asset.symbol_or_name()} as a cowswap fee',  # noqa: E501
                )
                decoded_events.append(fee_event)

            trades_events.append((spend_event, receive_event, fee_event, swap_data))

        return trades_events

    def _aggregator_post_decoding(
            self,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            all_logs: list[EvmTxReceiptLog],
    ) -> list['EvmEvent']:
        """
        Decodes cowswap trades.
        1. Goes through all the emitted Trade events.
        2. Filters out trades that are not relevant to the tracked accounts.
        3. For each trade finds or generates if missing spend and receive events.
        4. Makes sure that spend-receive pairs are consecutive.
        """
        all_swap_data = self._find_trades(tx_hash=transaction.tx_hash, all_logs=all_logs)
        relevant_trades = self._detect_relevant_trades(
            transaction=transaction,
            all_swap_data=all_swap_data,
            decoded_events=decoded_events,
        )
        for spend_event, receive_event, fee_event, swap_data in relevant_trades:
            spend_event.amount = swap_data.from_amount
            spend_event.counterparty = CPT_COWSWAP
            spend_event.event_type = HistoryEventType.TRADE
            receive_event.event_type = HistoryEventType.TRADE
            spend_event.event_subtype = HistoryEventSubType.SPEND
            receive_event.event_subtype = HistoryEventSubType.RECEIVE
            spend_event.notes = f'Swap {spend_event.amount} {spend_event.asset.symbol_or_name()} in a cowswap {swap_data.order_type} order'  # noqa: E501
            receive_event.notes = f'Receive {receive_event.amount} {receive_event.asset.symbol_or_name()} as the result of a cowswap {swap_data.order_type} order'  # noqa: E501
            maybe_reshuffle_events(
                ordered_events=[spend_event, receive_event, fee_event],
                events_list=decoded_events,
            )

        return decoded_events

    @staticmethod
    def _match_cowswap_counterparty(context: DecoderContext) -> EvmDecodingOutput:
        """Sets the CowSwap counterparty for events involving the settlement contract.

        This is needed because not all CowSwap transactions are sent directly
        to the settlement contract address.

        We don't decode the actual swap here since only one leg (spend or receive)
        is available at this stage. Full swap decoding happens in post-processing.
        """
        return EvmDecodingOutput(matched_counterparty=CPT_COWSWAP)

    # -- DecoderInterface methods

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (COWSWAP_CPT_DETAILS,)

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            **dict.fromkeys(self.native_asset_flow_addresses, (self._decode_native_asset_orders,)),
            self.settlement_address: (self._match_cowswap_counterparty,),
        }

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return {self.settlement_address: CPT_COWSWAP}

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_COWSWAP: [(0, self._aggregator_post_decoding)]}


class CowswapCommonDecoderWithVCOW(CowswapCommonDecoder):
    """Cowswap common decoder for chains that have the COW token"""

    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer | ArbitrumOneInquirer | GnosisInquirer | BaseInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            native_asset: Asset,
            wrapped_native_asset: Asset,
            vcow_token: Asset,
            cow_token: Asset,
            gno_token: Asset,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            native_asset=native_asset,
            wrapped_native_asset=wrapped_native_asset,
        )
        self.vcow_token = vcow_token.resolve_to_evm_token()
        self.cow_token = cow_token.resolve_to_evm_token()
        self.gno_token = gno_token.resolve_to_evm_token()

    def _aggregator_post_decoding(
            self,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        decoded_events = super()._aggregator_post_decoding(
            transaction=transaction,
            decoded_events=decoded_events,
            all_logs=all_logs,
        )

        # else check if it's a vested claim and make sure out event comes first and fix notes
        # notes fixing is needed only in gnosis but for consistency move notes populating here
        out_event, in_event = None, None
        for event in decoded_events:
            if event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.RETURN_WRAPPED and event.counterparty == CPT_COWSWAP and event.asset == self.vcow_token:  # noqa: E501
                out_event = event
                event.notes = f'Exchange {event.amount} vested vCOW for COW'
            elif event.event_type == HistoryEventType.WITHDRAWAL and event.event_subtype == HistoryEventSubType.REDEEM_WRAPPED and event.counterparty == CPT_COWSWAP and event.asset == self.cow_token:  # noqa: E501
                in_event = event
                event.notes = f'Claim {event.amount} COW from vesting tokens'

        if out_event and in_event:
            maybe_reshuffle_events(
                ordered_events=[out_event, in_event],
                events_list=decoded_events,
            )
        return decoded_events

    def _decode_normal_claim(self, context: DecoderContext) -> EvmDecodingOutput:
        raw_amount = int.from_bytes(context.tx_log.data[128:160])
        amount = asset_normalized_value(amount=raw_amount, asset=self.vcow_token)
        airdrop_identifier: Literal['cow_mainnet', 'cow_gnosis'] = 'cow_mainnet' if self.node_inquirer.chain_id == ChainID.ETHEREUM else 'cow_gnosis'  # noqa: E501
        # claimTypes with payment: 1=GnoOption, 2=UserOption, 3=Investor
        claim_supports_payment = int.from_bytes(context.tx_log.data[32:64]) in (1, 2, 3)
        claimant_address = bytes_to_address(context.tx_log.data[64:96])
        if not self.base.is_tracked(claimant_address):
            return DEFAULT_EVM_DECODING_OUTPUT
        claim_has_payment = False
        out_event = in_event = None
        for event in context.decoded_events:
            # Claim event always follows payment. Continue on payment, break on claim.
            if (
                claim_supports_payment and
                event.location_label == claimant_address and
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset in (self.node_inquirer.native_token, self.gno_token)
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.notes = f'Pay {event.amount} {event.asset.symbol_or_name()} to claim vCOW'
                event.counterparty = CPT_COWSWAP
                claim_has_payment = True
                out_event = event
                continue
            if match_airdrop_claim(
                event,
                user_address=bytes_to_address(context.tx_log.data[64:96]),
                amount=amount,
                asset=self.vcow_token,
                counterparty=CPT_COWSWAP,
                airdrop_identifier=airdrop_identifier,
            ):
                if claim_has_payment:
                    event.event_type = HistoryEventType.TRADE
                    event.event_subtype = HistoryEventSubType.RECEIVE
                    in_event = event
                break

        else:
            log.error(f'Could not find the normal COW token claim for {self.node_inquirer.chain_name} transaction {context.transaction.tx_hash.hex()}')  # noqa: E501

        if claim_has_payment:
            if in_event is not None:
                maybe_reshuffle_events(
                    ordered_events=[out_event, in_event],
                    events_list=context.decoded_events,
                )
            else:
                log.error(f'Could not find the COW token claim corresponding to detected payment for {self.node_inquirer.chain_name} transaction {context.transaction.tx_hash.hex()}')  # noqa: E501

        return EvmDecodingOutput(process_swaps=True)

    def _decode_vested_claim(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode a claim of vested cow token from vcow token"""
        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        # in gnosis chain the Vested log event has no amount in data. So we don't
        # match on amount for action items and in post decoding fix notes instead of here
        amount = token_normalized_value(int.from_bytes(context.tx_log.data), self.vcow_token) if self.node_inquirer.chain_id != ChainID.GNOSIS else None  # noqa: E501
        return EvmDecodingOutput(
            action_items=[
                ActionItem(
                    action='transform',
                    from_event_type=x[0],
                    from_event_subtype=x[1],
                    asset=x[2],
                    amount=amount,
                    location_label=user_address,
                    to_event_type=x[3],
                    to_event_subtype=x[4],
                    to_counterparty=CPT_COWSWAP,
                    to_address=x[2].evm_address,
                ) for x in (
                    (HistoryEventType.SPEND, HistoryEventSubType.NONE, self.vcow_token, HistoryEventType.SPEND, HistoryEventSubType.RETURN_WRAPPED),  # noqa: E501
                    (HistoryEventType.RECEIVE, HistoryEventSubType.NONE, self.cow_token, HistoryEventType.WITHDRAWAL, HistoryEventSubType.REDEEM_WRAPPED),  # noqa: E501
                )
            ],
        )

    def _decode_cow_claim(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode claim of cow token either normally or from vcow token"""
        if context.tx_log.topics[0] == CLAIMED:
            return self._decode_normal_claim(context)
        elif context.tx_log.topics[0] == VESTED:
            return self._decode_vested_claim(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return super().addresses_to_decoders() | {
            self.vcow_token.evm_address: (self._decode_cow_claim,),
        }

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return super().addresses_to_counterparties() | {
            self.vcow_token.evm_address: CPT_COWSWAP,
        }
