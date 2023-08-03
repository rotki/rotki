import logging
from typing import Any
from rotkehlchen.accounting.structures.balance import Balance

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
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
from rotkehlchen.utils.misc import hex_or_bytes_to_address

from .constants import CPT_DIVA, DIVA_ADDRESS

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
DELEGATE_CHANGED = b'14\xe8\xa2\xe6\xd9~\x92\x9a~T\x01\x1e\xa5H]}\x19m\xd5\xf0\xbaMN\xf9X\x03\xe8\xe3\xfc%\x7f'  # noqa: E501


class DivaDecoder(DecoderInterface):

    def _decode_delegation_change(self, context: DecoderContext) -> DecodingOutput:
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
            asset=A_ETH,
            balance=Balance(),
            location_label=event_address,
            notes=f'{delegator} started to delegate on DIVA to {delegate}',
            counterparty=CPT_DIVA,
        )
        return DecodingOutput(event=event, refresh_balances=False)

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
        }

    def counterparties(self) -> list[CounterpartyDetails]:
        return [CounterpartyDetails(identifier=CPT_DIVA, label='Diva', image='diva.svg')]
