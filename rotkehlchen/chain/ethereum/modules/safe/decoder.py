import logging
from typing import Any

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address

from .constants import CPT_SAFE, SAFE_VESTING

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SafeDecoder(DecoderInterface):
    """Decoder for ethereum mainnet safe (mostly token) related activities"""

    def _decode_safe_vesting(self, context: DecoderContext) -> DecodingOutput:
        account = hex_or_bytes_to_address(context.tx_log.topics[2])
        beneficiary = hex_or_bytes_to_address(context.tx_log.topics[3])
        if not self.base.any_tracked((account, beneficiary)):
            return DEFAULT_DECODING_OUTPUT

        notes = 'Claim {amount} SAFE from vesting'  # amount set at actionitem process
        if account != beneficiary:
            notes += f' and send to {beneficiary}'
        return DecodingOutput(
            action_items=[ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=EvmToken('eip155:1/erc20:0x5aFE3855358E112B5647B952709E6165e1c1eEEe'),
                to_notes=notes,
                to_counterparty=CPT_SAFE,
                to_address=SAFE_VESTING,
            )],
        )

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {SAFE_VESTING: (self._decode_safe_vesting,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_SAFE,
            label='Safe',
            image='safemultisig.svg',
        ),)
