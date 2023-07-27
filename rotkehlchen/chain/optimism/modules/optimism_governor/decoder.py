import logging
from typing import Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.decoding.constants import OPTIMISM_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails, EventCategory
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.constants import CPT_OPTIMISM
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, DecoderEventMappingType
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

GOVERNOR_ADDRESS = string_to_evm_address('0xcDF27F107725988f2261Ce2256bDfCdE8B382B10')

VOTE_CAST = b'\xb8\xe18\x88}\n\xa1;\xabD~\x82\xde\x9d\\\x17w\x04\x1e\xcd!\xca6\xba\x82O\xf1\xe6\xc0}\xdd\xa4'  # noqa: E501
VOTE_CAST_WITH_PARAMS = b'\xe2\xba\xbf\xba\xc5\x88\x9ap\x9bc\xbb\x7fY\x8b2N\x08\xbcZO\xb9\xecd\x7f\xb3\xcb\xc9\xec\x07\xeb\x87\x12'  # noqa: E501


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OptimismGovernorDecoder(DecoderInterface):
    def _decode_vote_cast(self, context: DecoderContext) -> DecodingOutput:
        """Decodes a vote cast event"""
        if context.tx_log.topics[0] not in (VOTE_CAST, VOTE_CAST_WITH_PARAMS):
            return DEFAULT_DECODING_OUTPUT  # for params event is same + params argument. Ignore it

        voter_address = hex_or_bytes_to_address(context.tx_log.topics[1])
        if not self.base.is_tracked(voter_address):
            return DEFAULT_DECODING_OUTPUT

        proposal_id = str(hex_or_bytes_to_int(context.tx_log.data[:32]))
        supports = bool(hex_or_bytes_to_int(context.tx_log.data[32:64]))
        notes = f'Voted {"FOR" if supports else "AGAINST"} optimism governance proposal https://vote.optimism.io/proposals/{proposal_id}'  # noqa: E501
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=A_ETH,
            balance=Balance(),
            location_label=voter_address,
            notes=notes,
            address=context.tx_log.address,
            counterparty=CPT_OPTIMISM,
        )
        return DecodingOutput(event=event)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            GOVERNOR_ADDRESS: (self._decode_vote_cast,),
        }

    def possible_events(self) -> DecoderEventMappingType:
        return {CPT_OPTIMISM: {
            HistoryEventType.INFORMATIONAL: {
                HistoryEventSubType.GOVERNANCE: EventCategory.GOVERNANCE,
            },
        }}

    def counterparties(self) -> list[CounterpartyDetails]:
        return [OPTIMISM_CPT_DETAILS]
