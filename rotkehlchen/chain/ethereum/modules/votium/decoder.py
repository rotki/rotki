import logging
from typing import Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CLAIMED, CPT_VOTIUM, VOTIUM_CONTRACTS

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class VotiumDecoder(EvmDecoderInterface):

    def _decode_claim(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != CLAIMED:
            return DEFAULT_EVM_DECODING_OUTPUT

        claimed_token_address = bytes_to_address(context.tx_log.topics[1])
        claimed_token = self.base.get_or_create_evm_token(claimed_token_address)
        receiver = bytes_to_address(context.tx_log.topics[2])
        claimed_amount_raw = int.from_bytes(context.tx_log.data[32:64])
        amount = asset_normalized_value(amount=claimed_amount_raw, asset=claimed_token)

        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.location_label == receiver and event.amount == amount and claimed_token == event.asset:  # noqa: E501
                try:
                    crypto_asset = event.asset.resolve_to_crypto_asset()
                except (UnknownAsset, WrongAssetType):
                    self.notify_user(event=event, counterparty=CPT_VOTIUM)
                    continue
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_VOTIUM
                event.notes = f'Receive {event.amount} {crypto_asset.symbol} from votium bribe'
                break

        else:  # not found
            log.error(f'Votium bribe transfer was not found for {context.transaction.tx_hash!s}')

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(VOTIUM_CONTRACTS, (self._decode_claim,))

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_VOTIUM, label='Votium', image='votium.png'),)
