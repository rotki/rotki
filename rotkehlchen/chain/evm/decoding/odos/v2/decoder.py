import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.abi import decode_event_data_abi_str
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.odos.v2.constants import CPT_ODOS_V2, SWAPMULTI_EVENT_ABI
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.transactions import EvmTransactions
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTokenKind
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Odosv2DecoderBase(DecoderInterface):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            router_address: ChecksumEvmAddress,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.evm_txns = EvmTransactions(self.evm_inquirer, self.base.database)
        self.router_address = router_address
        self.native_currency = self.evm_inquirer.native_token

    def _resolve_tokens_data(
            self,
            token_addresses: list['ChecksumEvmAddress'],
            token_amounts: list[int],
    ) -> dict[str, FVal]:
        """Returns the resolved evm tokens or native currency and their amounts"""
        resolved_result: dict[str, FVal] = {}
        for token_address, token_amount in zip(token_addresses, token_amounts, strict=True):
            if token_address == ZERO_ADDRESS:
                asset = self.native_currency
            else:
                asset = get_or_create_evm_token(
                    userdb=self.base.database,
                    evm_inquirer=self.base.evm_inquirer,
                    evm_address=token_address,
                    chain_id=self.base.evm_inquirer.chain_id,
                    token_kind=EvmTokenKind.ERC20,
                )

            resolved_result[asset.identifier] = asset_normalized_value(amount=token_amount, asset=asset)  # noqa: E501

        return resolved_result

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
                    chain_id=self.evm_inquirer.chain_id,
                    token_type=EvmTokenKind.ERC20,
                )) not in output_tokens)
            ):
                continue

            # can directly initialize EvmToken here because it's in output_tokens which were get_or_created above  # noqa: E501
            asset = EvmToken(identifier)
            if hex_or_bytes_to_address(tx_log.topics[2]) == self.router_address:
                router_holding_amount[asset] += asset_normalized_value(amount=hex_or_bytes_to_int(tx_log.data), asset=asset)  # noqa: E501

            elif hex_or_bytes_to_address(tx_log.topics[1]) == self.router_address:
                router_holding_amount[asset] -= asset_normalized_value(amount=hex_or_bytes_to_int(tx_log.data), asset=asset)  # noqa: E501

        if self.native_currency.identifier in output_tokens:
            try:  # download (if not there) and find all native token transfers from/to the router
                internal_native_ins = self.evm_txns.get_and_ensure_internal_txns_of_parent_in_db(
                    tx_hash=context.transaction.tx_hash,
                    to_address=self.router_address,
                    user_address=sender,
                )
                internal_native_outs = self.evm_txns.get_and_ensure_internal_txns_of_parent_in_db(
                    tx_hash=context.transaction.tx_hash,
                    from_address=self.router_address,
                    to_address=sender,
                    user_address=sender,
                )
            except RemoteError as e:
                log.error(f'Failed to get internal transactions for odos v2 swap {context.transaction} due to {e!s}')  # noqa: E501
            else:
                for internal_native_in in internal_native_ins:
                    router_holding_amount[self.native_currency] += asset_normalized_value(amount=internal_native_in.value, asset=self.native_currency)  # noqa: E501
                for internal_native_out in internal_native_outs:
                    router_holding_amount[self.native_currency] -= asset_normalized_value(amount=internal_native_out.value, asset=self.native_currency)  # noqa: E501

        return [
            self.base.make_event_next_index(
                tx_hash=context.transaction.tx_hash,
                timestamp=context.transaction.timestamp,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=held_asset,
                balance=Balance(amount=amount),
                location_label=sender,
                notes=f'Spend {amount} {held_asset.symbol_or_name()} as an Odos v2 fee',
                counterparty=CPT_ODOS_V2,
                address=self.router_address,
            )
            for held_asset, amount in router_holding_amount.items()
            if amount != ZERO
        ]

    def _decode_swap(self, context: 'DecoderContext') -> 'DecodingOutput':
        """Decodes swaps done using an Odos v2 router"""
        if context.tx_log.topics[0] == b'\x82>\xaf\x01\x00-sS\xfb\xca\xdb.\xa30\\\xc4o\xa3]y\x9c\xb0\x91HF\xd1\x85\xac\x06\xf8\xad\x05':  # swapCompact()  # noqa: E501
            # decode the single swap event structure
            # https://github.com/odos-xyz/odos-router-v2/blob/main/contracts/OdosRouterV2.sol#L64
            decoded_data: tuple[ChecksumEvmAddress, list[int], list[ChecksumEvmAddress], list[int], list[ChecksumEvmAddress]] = (  # noqa: E501
                hex_or_bytes_to_address(context.tx_log.data[0:32]),  # sender
                [hex_or_bytes_to_int(context.tx_log.data[32:64])],  # input amount
                [hex_or_bytes_to_address(context.tx_log.data[64:96])],  # input token address
                [hex_or_bytes_to_int(context.tx_log.data[96:128])],  # output amount
                [hex_or_bytes_to_address(context.tx_log.data[128:160])],  # output token address
            )
        elif context.tx_log.topics[0] == b'}\x7f\xb05\x18%:\xe0\x19\x13Sf(\xb7\x8dm\x82\xe6>\x19\xb9C\xaa\xb5\xf4\x94\x83V\x02\x12Y\xbe':  # swapMultiCompact()  # noqa: E501
            try:
                # decode the multi swap event structure
                # https://github.com/odos-xyz/odos-router-v2/blob/main/contracts/OdosRouterV2.sol#L74
                _, decoded_data = decode_event_data_abi_str(context.tx_log, SWAPMULTI_EVENT_ABI)  # type: ignore[assignment]  # types are known from the ABI
            except DeserializationError as e:
                log.error(
                    f'Failed to deserialize Odos event {context.tx_log=} at '
                    f'{context.transaction} due to {e}',
                )
                return DEFAULT_DECODING_OUTPUT
        else:
            return DEFAULT_DECODING_OUTPUT

        if not self.base.is_tracked(decoded_data[0]):
            return DEFAULT_DECODING_OUTPUT

        input_tokens = self._resolve_tokens_data(token_amounts=decoded_data[1], token_addresses=decoded_data[2])  # noqa: E501
        output_tokens = self._resolve_tokens_data(token_amounts=decoded_data[3], token_addresses=decoded_data[4])  # noqa: E501

        in_events, out_events = [], []
        for event in context.decoded_events:
            if (
                ((input_amount := input_tokens.get(event.asset.identifier)) == event.balance.amount) or  # noqa: E501
                input_amount == ZERO  # this means https://docs.odos.xyz/product/sor/v2/#max-balance-swapping  # noqa: E501
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
                event.notes = f'Swap {event.balance.amount} {event.asset.symbol_or_name()} in Odos v2'  # noqa: E501
                event.address = self.router_address
                event.counterparty = CPT_ODOS_V2
                out_events.append(event)

            elif output_tokens.get(event.asset.identifier) == event.balance.amount and (
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
                event.notes = f'Receive {event.balance.amount} {event.asset.symbol_or_name()} as the result of a swap in Odos v2'  # noqa: E501
                event.address = self.router_address
                event.counterparty = CPT_ODOS_V2
                in_events.append(event)

        context.decoded_events.extend(fee_events := self._calculate_router_fee(
            context=context,
            sender=decoded_data[0],
            output_tokens=output_tokens,
        ))
        maybe_reshuffle_events(
            ordered_events=out_events + in_events + fee_events,
            events_list=context.decoded_events,
        )
        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.router_address: (self._decode_swap,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_ODOS_V2,
            label='Odos v2',
            image='odos.svg',
        ),)
