import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails, EventCategory
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DIVA
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, DecoderEventMappingType
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import CPT_DIVA, DIVA_ADDRESS

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
DELEGATE_CHANGED = b'14\xe8\xa2\xe6\xd9~\x92\x9a~T\x01\x1e\xa5H]}\x19m\xd5\xf0\xbaMN\xf9X\x03\xe8\xe3\xfc%\x7f'  # noqa: E501
CLAIM_AIRDROP = b'N\xc9\x0e\x96U\x19\xd9&\x81&tg\xf7u\xad\xa5\xbd!J\xa9,\r\xc9=\x90\xa5\xe8\x80\xce\x9e\xd0&'  # noqa: E501
DIVA_AIDROP_CONTRACT = string_to_evm_address('0x777E2B2Cc7980A6bAC92910B95269895EEf0d2E8')


class DivaDecoder(DecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.diva = A_DIVA.resolve_to_evm_token()

    def _decode_delegation_change(self, context: DecoderContext) -> DecodingOutput:
        """Decode a change in the delegated address"""
        if context.tx_log.topics[0] != DELEGATE_CHANGED:
            return DEFAULT_DECODING_OUTPUT

        delegator = hex_or_bytes_to_address(context.tx_log.topics[1])
        delegate = hex_or_bytes_to_address(context.tx_log.topics[3])

        if self.base.is_tracked(delegator):
            event_address = delegator
        else:
            event_address = delegate

        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=self.diva,
            balance=Balance(),
            location_label=event_address,
            notes=f'Change DIVA Delegate from {delegator} to {delegate}',
            counterparty=CPT_DIVA,
        )
        return DecodingOutput(event=event, refresh_balances=False)

    def _decode_diva_claim(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != CLAIM_AIRDROP:
            return DEFAULT_DECODING_OUTPUT

        claiming_address = hex_or_bytes_to_address(context.tx_log.data[32:64])
        claimed_amount = token_normalized_value(
            token_amount=hex_or_bytes_to_int(context.tx_log.data[64:]),
            token=self.diva,
        )

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.location_label == claiming_address and
                event.asset == self.diva and
                event.balance.amount == claimed_amount
            ):
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.AIRDROP
                event.counterparty = CPT_DIVA
                event.notes = f'Claim {event.balance.amount} DIVA from the DIVA airdrop'
                break

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def possible_events(self) -> DecoderEventMappingType:
        return {CPT_DIVA: {
            HistoryEventType.INFORMATIONAL: {
                HistoryEventSubType.GOVERNANCE: EventCategory.GOVERNANCE,
            },
        }}

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            DIVA_ADDRESS: (self._decode_delegation_change,),
            DIVA_AIDROP_CONTRACT: (self._decode_diva_claim,),
        }

    def counterparties(self) -> list[CounterpartyDetails]:
        return [CounterpartyDetails(identifier=CPT_DIVA, label='Diva', image='diva.svg')]
