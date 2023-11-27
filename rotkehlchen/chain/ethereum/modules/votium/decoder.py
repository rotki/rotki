import logging
from typing import Any

from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import CPT_VOTIUM

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

VOTIUM_CLAIM = b'Gf\x92\x1f\\Ydm"\xd7\xd2f\xa2\x91d\xc8\xe9b6\x84\xd8\xdf\xdb\xd91s\x1d\xfd\xca\x02R8'  # noqa: E501
VOTIUM_CONTRACT = string_to_evm_address('0x378Ba9B73309bE80BF4C2c027aAD799766a7ED5A')


class VotiumDecoder(DecoderInterface):

    def _decode_claim(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != VOTIUM_CLAIM:
            return DEFAULT_DECODING_OUTPUT

        claimed_token_address = hex_or_bytes_to_address(context.tx_log.topics[1])
        claimed_token = self.base.get_or_create_evm_token(claimed_token_address)
        receiver = hex_or_bytes_to_address(context.tx_log.topics[2])
        claimed_amount_raw = hex_or_bytes_to_int(context.tx_log.data[32:64])
        amount = asset_normalized_value(amount=claimed_amount_raw, asset=claimed_token)

        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.location_label == receiver and event.balance.amount == amount and claimed_token == event.asset:  # noqa: E501
                try:
                    crypto_asset = event.asset.resolve_to_crypto_asset()
                except (UnknownAsset, WrongAssetType):
                    self.notify_user(event=event, counterparty=CPT_VOTIUM)
                    continue
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_VOTIUM
                event.notes = f'Receive {event.balance.amount} {crypto_asset.symbol} from votium bribe'  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            VOTIUM_CONTRACT: (self._decode_claim,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_VOTIUM, label='Votium', image='votium.png'),)
