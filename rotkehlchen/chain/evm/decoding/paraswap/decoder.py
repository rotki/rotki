import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import CryptoAsset, EvmToken
from rotkehlchen.chain.ethereum.modules.uniswap.v2.constants import SWAP_SIGNATURE
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.uniswap.v3.constants import DIRECT_SWAP_SIGNATURE
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.transactions import EvmTransactions
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import (
    BUY_ON_UNISWAP_V2_FORK,
    BUY_SIGNATURE,
    CPT_PARASWAP,
    SWAP_ON_UNISWAP_V2_FACTORY,
    SWAP_ON_UNISWAP_V2_FORK,
    SWAP_ON_UNISWAP_V2_FORK_WITH_PERMIT,
    SWAP_SIGNATURE as PARASWAP_SWAP_SIGNATURE,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ParaswapCommonDecoder(DecoderInterface):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            router_address: ChecksumEvmAddress,
            fee_receiver_address: ChecksumEvmAddress,
    ) -> None:
        super().__init__(evm_inquirer, base_tools, msg_aggregator)
        self.evm_txns = EvmTransactions(self.evm_inquirer, self.base.database)
        self.router_address = router_address
        self.fee_receiver_address = fee_receiver_address

    def _decode_swap(
            self,
            context: DecoderContext,
            receiver: ChecksumEvmAddress,
            sender: ChecksumEvmAddress,
    ) -> DecodingOutput:
        """This function is used to decode the swap done by paraswap."""
        if not self.base.any_tracked((sender, receiver)):
            return DEFAULT_DECODING_OUTPUT

        out_event: EvmEvent | None = None
        in_event: EvmEvent | None = None
        partial_refund_event: EvmEvent | None = None
        fee_event: EvmEvent | None = None
        fee_asset: CryptoAsset | None = None
        for event in context.decoded_events:
            if sender != event.location_label:  # in this case, it's not a valid send/receive event
                continue
            if (
                (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.SPEND) or  # noqa: E501
                (event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE)  # noqa: E501
            ):  # find the send event
                event.counterparty = CPT_PARASWAP
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.address = self.router_address
                # not modifying event.notes here since that's done after partial refund below
                out_event = event
            elif (
                (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.RECEIVE) or  # noqa: E501
                (event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE)  # noqa: E501
            ):  # find the receive event
                event.counterparty = CPT_PARASWAP
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {event.balance.amount} {event.asset.resolve_to_asset_with_symbol().symbol} as the result of a swap in paraswap'  # noqa: E501
                event.address = self.router_address
                if in_event is None:
                    in_event = event
                else:  # if another in_event is found, then it is a partial refund of in_asset
                    partial_refund_event = event

        if in_event is None or out_event is None:
            log.error(f'Could not find the corresponding events when decoding {self.evm_inquirer.chain_name} paraswap swap {context.transaction.tx_hash.hex()}')  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        if partial_refund_event is not None:  # if some in_asset is returned back.
            # it's assumed in the above for loop, that the second in_event is the partial refund
            # we verify below if the assumption is wrong, by checking the asset's similarity
            # we check it here instead of in the for loop above because, out_event could be None
            # at the time of the check
            if in_event.asset == out_event.asset:  # if this is true, then assumption is wrong
                partial_refund_event, in_event = in_event, partial_refund_event  # swap them
            out_event.balance.amount -= partial_refund_event.balance.amount  # adjust the amount
            context.decoded_events.remove(partial_refund_event)  # and remove it from the list
        out_event.notes = f'Swap {out_event.balance.amount} {out_event.asset.resolve_to_asset_with_symbol().symbol} in paraswap'  # noqa: E501

        fee_raw: int | None = None
        # assets can be native currency, so resolve them to CryptoAsset instead of EvmToken
        out_asset = out_event.asset.resolve_to_crypto_asset()
        in_asset = in_event.asset.resolve_to_crypto_asset()
        for log_event in context.all_logs:  # extract the fee info
            if (
                log_event.topics[0] == ERC20_OR_ERC721_TRANSFER and
                hex_or_bytes_to_address(log_event.topics[1]) == self.router_address and
                hex_or_bytes_to_address(log_event.topics[2]) == self.fee_receiver_address
            ):
                if isinstance(in_asset, EvmToken) and in_asset.evm_address == log_event.address:
                    fee_asset = in_asset
                elif isinstance(out_asset, EvmToken) and out_asset.evm_address == log_event.address:  # noqa: E501
                    fee_asset = out_asset
                fee_raw = hex_or_bytes_to_int(log_event.data)
                break
        else:  # if no fee is found yet, check if fee is paid through internal transactions in the native token  # noqa: E501
            try:
                internal_fee_txs = self.evm_txns.get_and_ensure_internal_txns_of_parent_in_db(
                    tx_hash=context.transaction.tx_hash,
                    from_address=self.router_address,
                    to_address=self.fee_receiver_address,
                    user_address=sender,
                )
            except RemoteError as e:
                log.error(f'Failed to get internal transactions for paraswap {self.evm_inquirer.chain_name} swap {context.transaction.tx_hash.hex()} due to {e!s}')  # noqa: E501
            else:
                if len(internal_fee_txs) > 0:
                    fee_raw = internal_fee_txs[0].value  # assuming only one tx from router to fee claimer  # noqa: E501
                    fee_asset = self.base.evm_inquirer.native_token

        if fee_raw is not None and fee_asset is not None:
            fee_amount = asset_normalized_value(amount=fee_raw, asset=fee_asset)
            if fee_asset == in_asset:
                # update the in_event to adjust its balance since the amount used in fees
                # was also received as part of the swap
                in_event.balance.amount += fee_amount
                in_event.notes = f'Receive {in_event.balance.amount} {fee_asset.symbol} as the result of a swap in paraswap'  # noqa: E501

            # And now create a new event for the fee
            fee_event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=fee_asset,
                balance=Balance(amount=fee_amount),
                location_label=sender,
                notes=f'Spend {fee_amount} {fee_asset.symbol} as a paraswap fee',
                counterparty=CPT_PARASWAP,
                address=context.transaction.to_address,
            )
            context.decoded_events.append(fee_event)

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event, fee_event],
            events_list=context.decoded_events,
        )
        return DEFAULT_DECODING_OUTPUT

    def _decode_paraswap_swap(self, context: DecoderContext) -> DecodingOutput:
        """This decodes the following types of trades:
        - Simple Buy
        - Simple Swap
        - Multi Swap
        - Mega Swap
        - Direct Swap on Uniswap V3
        - Direct Swap on Curve V1 and V2
        - Direct Swap on Balancer V2"""
        if context.tx_log.topics[0] not in {PARASWAP_SWAP_SIGNATURE, BUY_SIGNATURE, DIRECT_SWAP_SIGNATURE}:  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        return self._decode_swap(
            context=context,
            receiver=hex_or_bytes_to_address(context.tx_log.topics[1]),
            sender=hex_or_bytes_to_address(context.tx_log.data[96:128]),
        )

    def _decode_uniswap_v2_swap(self, context: DecoderContext) -> DecodingOutput:
        """This decodes swaps done directly on Uniswap V2 pools"""
        return self._decode_swap(
            context=context,
            receiver=hex_or_bytes_to_address(context.tx_log.topics[2]),
            sender=context.transaction.from_address,
        )

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            self.router_address: (self._decode_paraswap_swap,),
        }

    def decoding_by_input_data(self) -> dict[bytes, dict[bytes, Callable]]:
        return {
            method_id: {SWAP_SIGNATURE: self._decode_uniswap_v2_swap}
            for method_id in (
                SWAP_ON_UNISWAP_V2_FORK,
                SWAP_ON_UNISWAP_V2_FACTORY,
                SWAP_ON_UNISWAP_V2_FORK_WITH_PERMIT,
                BUY_ON_UNISWAP_V2_FORK,
            )
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_PARASWAP,
            label='Paraswap',
            image='paraswap.svg',
        ),)
