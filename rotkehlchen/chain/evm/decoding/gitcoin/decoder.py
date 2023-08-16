import logging
from abc import ABCMeta
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GITCOIN, GITCOIN_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails, EventCategory
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, DecoderEventMappingType
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

VOTED = b'\xbf5\xc00\x17\x8a\x1eg\x8c\x82\x96\xa4\xe5\x08>\x90!\xa2L\x1a\x1d\xef\xa5\xbf\xbd\xfd\xe7K\xce\xcf\xa3v'  # noqa: E501


class GitcoinV2CommonDecoder(DecoderInterface, metaclass=ABCMeta):
    """This is the gitcoin v2 (allo protocol) common decoder

    Not the same as gitcoin v1, or v1.5 (they have changed contracts many times).

    Each round seems to have their own implementation contract address and we need to be
    adding them as part of the constructor here to create the proper mappings.
    """

    def __init__(  # pylint: disable=super-init-not-called
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            round_impl_addresses: list['ChecksumEvmAddress'],
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.round_impl_addresses = round_impl_addresses
        self.eth = A_ETH.resolve_to_crypto_asset()

    def _decode_action(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == VOTED:
            return self._decode_voted(context)

        return DEFAULT_DECODING_OUTPUT

    def _decode_voted(self, context: DecoderContext) -> DecodingOutput:
        donator = hex_or_bytes_to_address(context.tx_log.data[64:96])
        receiver = hex_or_bytes_to_address(context.tx_log.data[96:128])
        donator_tracked = self.base.is_tracked(donator)
        receiver_tracked = self.base.is_tracked(receiver)
        if donator_tracked is False and receiver_tracked is False:
            return DEFAULT_DECODING_OUTPUT

        token_address = hex_or_bytes_to_address(context.tx_log.data[:32])
        if token_address == ZERO_ADDRESS:
            asset = self.eth
        else:
            asset = self.base.get_or_create_evm_token(token_address)
        amount_raw = hex_or_bytes_to_int(context.tx_log.data[32:64])
        amount = asset_normalized_value(amount_raw, asset)

        if donator_tracked and receiver_tracked:  # donating to himself??
            expected_type = HistoryEventType.TRANSFER
            verb = 'Transfer'
            preposition = 'to'
            target = receiver
        elif donator_tracked:
            expected_type = HistoryEventType.SPEND
            verb = 'Make'
            preposition = 'to'
            target = receiver
        else:  # only receiver tracked
            expected_type = HistoryEventType.RECEIVE
            verb = 'Receive'
            preposition = 'from'
            target = donator

        for event in context.decoded_events:
            if event.event_type == expected_type and event.event_subtype == HistoryEventSubType.NONE and event.asset == A_ETH and event.balance.amount == amount:  # noqa: E501
                event.event_subtype = HistoryEventSubType.DONATE
                event.counterparty = CPT_GITCOIN
                event.notes = f'{verb} a gitcoin donation of {amount} {asset.symbol} {preposition} {target}'  # noqa: E501
                break
        else:
            log.error(
                f'Could not find a corresponding event for gitcoin {verb} '
                f'{preposition} {target} in transaction {context.transaction.tx_hash.hex()}',
            )

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def possible_events(self) -> DecoderEventMappingType:
        return {CPT_GITCOIN: {
            HistoryEventType.SPEND: {
                HistoryEventSubType.DONATE: EventCategory.DONATE,
            },
            HistoryEventType.RECEIVE: {
                HistoryEventSubType.DONATE: EventCategory.RECEIVE_DONATION,
            },
            HistoryEventType.TRANSFER: {
                HistoryEventSubType.DONATE: EventCategory.DONATE,
            },
        }}

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            address: (self._decode_action,) for address in self.round_impl_addresses
        }

    def counterparties(self) -> list[CounterpartyDetails]:
        return [GITCOIN_CPT_DETAILS]
