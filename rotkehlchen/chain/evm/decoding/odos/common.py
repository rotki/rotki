import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import DecoderContext, EvmDecodingOutput
from rotkehlchen.chain.evm.transactions import EvmTransactions
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, TokenKind
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OdosCommonDecoderBase(EvmDecoderInterface):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            router_address: ChecksumEvmAddress,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.evm_txns = EvmTransactions(self.node_inquirer, self.base.database)
        self.router_address = router_address
        self.native_currency = self.node_inquirer.native_token
        self.label = self.counterparties()[0].label

    def _calculate_router_fee(
            self,
            context: 'DecoderContext',
            sender: 'ChecksumEvmAddress',
            output_tokens: dict[str, FVal],
    ) -> list[EvmEvent]:
        """Calculates the fees collected by the router and returns the fee events.
        Fees are the amount of out tokens that router received - the amount that router sent.
        `output_tokens` is a dictionary mapping from token identifier to the amount of tokens
        that were received by the user.
        """
        router_holding_amount: defaultdict[Asset, FVal] = defaultdict(FVal)
        for tx_log in context.all_logs:
            if (
                tx_log.topics[0] != ERC20_OR_ERC721_TRANSFER or
                ((identifier := evm_address_to_identifier(
                    address=tx_log.address,
                    chain_id=self.node_inquirer.chain_id,
                    token_type=TokenKind.ERC20,
                )) not in output_tokens)
            ):
                continue

            # can directly initialize EvmToken here because it's in output_tokens which were get_or_created above  # noqa: E501
            asset = EvmToken(identifier)
            if bytes_to_address(tx_log.topics[2]) == self.router_address:
                router_holding_amount[asset] += asset_normalized_value(amount=int.from_bytes(tx_log.data), asset=asset)  # noqa: E501

            elif bytes_to_address(tx_log.topics[1]) == self.router_address:
                router_holding_amount[asset] -= asset_normalized_value(amount=int.from_bytes(tx_log.data), asset=asset)  # noqa: E501

        if self.native_currency.identifier in output_tokens:
            try:  # download (if not there) and find all native token transfers from/to the router
                internal_native_ins = self.evm_txns.get_and_ensure_internal_txns_of_parent_in_db(
                    chain_id=self.base.evm_inquirer.chain_id,
                    tx_hash=context.transaction.tx_hash,
                    to_address=self.router_address,
                    user_address=sender,
                )
                internal_native_outs = self.evm_txns.get_and_ensure_internal_txns_of_parent_in_db(
                    chain_id=self.base.evm_inquirer.chain_id,
                    tx_hash=context.transaction.tx_hash,
                    from_address=self.router_address,
                    to_address=sender,
                    user_address=sender,
                )
            except RemoteError as e:
                log.error(f'Failed to get internal transactions for {self.label} swap {context.transaction} due to {e!s}')  # noqa: E501
            else:
                for internal_native_in in internal_native_ins:
                    router_holding_amount[self.native_currency] += asset_normalized_value(amount=internal_native_in.value, asset=self.native_currency)  # noqa: E501
                for internal_native_out in internal_native_outs:
                    router_holding_amount[self.native_currency] -= asset_normalized_value(amount=internal_native_out.value, asset=self.native_currency)  # noqa: E501

        router_fees = []
        for held_asset, amount in router_holding_amount.items():
            if amount < ZERO:
                log.error(
                    f'Miscalculated negative {self.label} router fees as {amount} '
                    f'{held_asset.symbol_or_name()} in {context.transaction}.',
                )
            elif amount > ZERO:
                router_fees.append(self.base.make_event_next_index(
                    tx_ref=context.transaction.tx_hash,
                    timestamp=context.transaction.timestamp,
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.FEE,
                    asset=held_asset,
                    amount=amount,
                    location_label=sender,
                    notes=f'Spend {amount} {held_asset.symbol_or_name()} as an {self.label} fee',
                    counterparty=self.counterparties()[0].identifier,
                    address=self.router_address,
                ))

        return router_fees

    def decode_swap(
            self,
            context: 'DecoderContext',
            sender: 'ChecksumEvmAddress',
            input_tokens: dict[str, FVal],
            output_tokens: dict[str, FVal],
    ) -> 'EvmDecodingOutput':
        """Decodes swaps done using an Odos v1/v2 router"""
        in_events, out_events = [], []
        for event in context.decoded_events:
            if (
                ((input_amount := input_tokens.get(event.asset.identifier)) == event.amount) or
                input_amount == ZERO  # this means https://docs.odos.xyz/build/quickstart/sor  # noqa: E501
            ) and (
                (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE
                ) or (
                    event.event_type == HistoryEventType.TRADE and
                    event.event_subtype == HistoryEventSubType.SPEND
                )
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.notes = f'Swap {event.amount} {event.asset.symbol_or_name()} in {self.label}'
                event.address = self.router_address
                event.counterparty = self.counterparties()[0].identifier
                out_events.append(event)

            elif output_tokens.get(event.asset.identifier) == event.amount and (
                (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE
                ) or (
                    event.event_type == HistoryEventType.TRADE and
                    event.event_subtype == HistoryEventSubType.RECEIVE
                )
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {event.amount} {event.asset.symbol_or_name()} as the result of a swap in {self.label}'  # noqa: E501
                event.address = self.router_address
                event.counterparty = self.counterparties()[0].identifier
                in_events.append(event)

        context.decoded_events.extend(fee_events := self._calculate_router_fee(
            context=context,
            sender=sender,
            output_tokens=output_tokens,
        ))
        maybe_reshuffle_events(
            ordered_events=out_events + in_events + fee_events,
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(process_swaps=True)
