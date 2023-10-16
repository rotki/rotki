import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import CPT_OCTANT, OCTANT_DEPOSITS

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

LOCKED = b'L\x00(\x1b\x0b\xce!\xcdpd N\x92\x14m\x97,5\x9c7C\xb9\xa5\x03\xf48\xb42^\xfa\xaf\x14'
UNLOCKED = b"\xc8f\xd6!,X\xa2H\nm\xa1O\x1b\xdb\xaa\xe0\xc1'\xcd\xc8)d\t\x15z#\xb9h\x14\x90f\xce"

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OctantDecoder(DecoderInterface):

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
        self.glm = get_or_create_evm_token(
            userdb=self.base.database,
            evm_address=string_to_evm_address('0x7DD9c5Cba05E151C895FDe1CF355C9A1D5DA6429'),
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=ethereum_inquirer,
        )

    def _decode_events(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] not in (LOCKED, UNLOCKED):
            return DEFAULT_DECODING_OUTPUT

        if context.tx_log.topics[0] == LOCKED:
            expected_type = HistoryEventType.SPEND
            new_type = HistoryEventType.DEPOSIT
            new_subtype = HistoryEventSubType.DEPOSIT_ASSET
            verb, preposition = 'Lock', 'in'
        elif context.tx_log.topics[0] == UNLOCKED:
            expected_type = HistoryEventType.RECEIVE
            new_type = HistoryEventType.WITHDRAWAL
            new_subtype = HistoryEventSubType.REMOVE_ASSET
            verb, preposition = 'Unlock', 'from'
        else:
            return DEFAULT_DECODING_OUTPUT

        raw_amount = hex_or_bytes_to_int(context.tx_log.data[32:64])
        address = hex_or_bytes_to_address(context.tx_log.data[96:128])
        if self.base.is_tracked(address) is False:
            return DEFAULT_DECODING_OUTPUT

        amount = token_normalized_value(raw_amount, self.glm)

        for event in context.decoded_events:
            if (
                    event.event_type == expected_type and
                    event.asset == self.glm and
                    event.address == OCTANT_DEPOSITS and
                    event.balance.amount == amount
            ):
                event.event_type = new_type
                event.event_subtype = new_subtype
                event.counterparty = CPT_OCTANT
                event.notes = f'{verb} {event.balance.amount} GLM {preposition} Octant'
                event.sequence_index = context.tx_log.log_index + 1  # push it after approval if any  # noqa: E501
                break

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {OCTANT_DEPOSITS: (self._decode_events,)}

    def counterparties(self) -> list[CounterpartyDetails]:
        return [CounterpartyDetails(
            identifier=CPT_OCTANT,
            label='Octant',
            image='octant.svg',
        )]
