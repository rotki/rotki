import logging
from abc import ABC
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import CryptoAsset, EvmToken
from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.transactions import EvmTransactions
from rotkehlchen.errors.misc import DataIntegrityError, RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_PARASWAP

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ParaswapCommonDecoder(EvmDecoderInterface, ABC):

    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
            router_address: ChecksumEvmAddress,
            fee_receiver_address: ChecksumEvmAddress,
    ) -> None:
        super().__init__(evm_inquirer, base_tools, msg_aggregator)
        self.evm_txns = EvmTransactions(self.node_inquirer, self.base.database)
        self.router_address = router_address
        self.fee_receiver_address = fee_receiver_address

    def _decode_swap(
            self,
            context: DecoderContext,
            sender: ChecksumEvmAddress,
            receiver: ChecksumEvmAddress | None = None,
            candidate_events: tuple[EvmEvent, EvmEvent] | None = None,
    ) -> EvmDecodingOutput:
        """This function is used to decode the swap done by paraswap.
        In v6 swaps, receiver is unavailable and is ignored,
        since sender should always be a tracked address.
        If the caller already matched the swap legs, only inspect those events.
        """
        if not self.base.any_tracked((sender,) if receiver is None else (sender, receiver)):
            return DEFAULT_EVM_DECODING_OUTPUT

        out_event: EvmEvent | None = None
        receive_events: list[EvmEvent] = []
        fee_event: EvmEvent | None = None
        fee_asset: CryptoAsset | None = None
        for event in context.decoded_events if candidate_events is None else candidate_events:
            if sender != event.location_label:  # in this case, it's not a valid send/receive event
                continue
            if (
                (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.SPEND) or  # noqa: E501
                (event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE)  # noqa: E501
            ):  # find the send event
                out_event = event
            elif (
                (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.RECEIVE) or  # noqa: E501
                (event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE)  # noqa: E501
            ):  # collect receive candidates; classified below once the spent asset is known
                receive_events.append(event)

        if out_event is None:
            log.error(
                'Could not find the corresponding events when decoding %s paraswap swap %s',
                self.node_inquirer.chain_name,
                context.transaction.tx_hash,
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        # the bought asset is the first received asset that differs from the spent one
        if (in_event := next((x for x in receive_events if x.asset != out_event.asset), None)) is None:  # noqa: E501
            log.error(
                'Could not find a receive event of an asset other than the spent %s when decoding %s paraswap swap %s',  # noqa: E501
                out_event.asset,
                self.node_inquirer.chain_name,
                context.transaction.tx_hash,
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        for event in receive_events:  # a receive of the spent asset is a partial refund of it
            if event.asset == out_event.asset:
                out_event.amount -= event.amount
                context.decoded_events.remove(event)

        out_event.counterparty = CPT_PARASWAP
        out_event.event_type = HistoryEventType.TRADE
        out_event.event_subtype = HistoryEventSubType.SPEND
        out_event.address = self.router_address
        out_event.notes = f'Swap {out_event.amount} {out_event.asset.resolve_to_asset_with_symbol().symbol} in paraswap'  # noqa: E501

        in_event.event_type = HistoryEventType.TRADE
        in_event.event_subtype = HistoryEventSubType.RECEIVE
        in_event.notes = f'Receive {in_event.amount} {in_event.asset.resolve_to_asset_with_symbol().symbol} as the result of a swap in paraswap'  # noqa: E501

        fee_raw: int | None = None
        # assets can be native currency, so resolve them to CryptoAsset instead of EvmToken
        out_asset = out_event.asset.resolve_to_crypto_asset()
        in_asset = in_event.asset.resolve_to_crypto_asset()
        for log_event in context.all_logs:  # extract the fee info
            if (
                log_event.topics[0] == ERC20_OR_ERC721_TRANSFER and
                bytes_to_address(log_event.topics[1]) == self.router_address and
                bytes_to_address(log_event.topics[2]) == self.fee_receiver_address
            ):
                if isinstance(in_asset, EvmToken) and in_asset.evm_address == log_event.address:
                    fee_asset = in_asset
                elif isinstance(out_asset, EvmToken) and out_asset.evm_address == log_event.address:  # noqa: E501
                    fee_asset = out_asset
                fee_raw = int.from_bytes(log_event.data)
                break
        else:  # if no fee is found yet, check if fee is paid through internal transactions in the native token  # noqa: E501
            try:
                internal_fee_txs = self.evm_txns.get_and_ensure_internal_txns_of_parent_in_db(
                    tx_hash=context.transaction.tx_hash,
                    chain_id=self.base.evm_inquirer.chain_id,
                    tx_timestamp=context.transaction.timestamp,
                    from_address=self.router_address,
                    to_address=self.fee_receiver_address,
                    user_address=sender,
                )
            except (RemoteError, DataIntegrityError) as e:
                log.error(f'Failed to get internal transactions for paraswap {self.node_inquirer.chain_name} swap {context.transaction.tx_hash!s} due to {e!s}')  # noqa: E501
            else:
                if len(internal_fee_txs) > 0:
                    fee_raw = internal_fee_txs[0].value  # assuming only one tx from router to fee claimer  # noqa: E501
                    fee_asset = self.base.evm_inquirer.native_token

        if fee_raw is not None and fee_asset is not None:
            fee_amount = asset_normalized_value(amount=fee_raw, asset=fee_asset)
            if fee_asset == in_asset:
                # update the in_event to adjust its balance since the amount used in fees
                # was also received as part of the swap
                in_event.amount += fee_amount
                in_event.notes = f'Receive {in_event.amount} {fee_asset.symbol} as the result of a swap in paraswap'  # noqa: E501

            # And now create a new event for the fee
            fee_event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.FEE,
                asset=fee_asset,
                amount=fee_amount,
                notes=f'Spend {fee_amount} {fee_asset.symbol} as a paraswap fee',
            )
            context.decoded_events.append(fee_event)

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event, fee_event],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(process_swaps=True)

    # -- DecoderInterface methods

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_PARASWAP,
            label='Paraswap',
            image='paraswap.svg',
        ),)
