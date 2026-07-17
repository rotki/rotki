import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.gnosis.modules.gnosisdao.constants import (
    CLAIMED_TOPIC,
    CPT_GNOSISDAO,
    DEPOSITED_TOPIC,
    GNOSISDAO_CPT_DETAILS,
    GNOSISDAO_TREASURY_SAFE,
    REDEMPTION_DEPOSIT_ADDRESS,
    REDEMPTION_DISTRIBUTOR_ADDRESS,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GnosisdaoDecoder(EvmDecoderInterface):
    """Decodes the GIP-151 GnosisDAO one-time pro-rata treasury redemption events"""

    def _decode_redemption_deposit(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode a GNO/osGNO deposit into the redemption deposit contract"""
        if context.tx_log.topics[0] != DEPOSITED_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        holder = bytes_to_address(context.tx_log.topics[1])
        token = self.base.get_or_create_evm_token(
            address=bytes_to_address(context.tx_log.topics[2]),
        )
        amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token=token,
        )
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.location_label == holder and
                    event.asset == token and
                    event.amount == amount
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_GNOSISDAO
                event.notes = f'Deposit {amount} {token.symbol} into the GnosisDAO treasury redemption'  # noqa: E501
                break
        else:
            log.error('Could not find GnosisDAO redemption deposit transfer in %s', context.transaction)  # noqa: E501

        return EvmDecodingOutput(matched_counterparty=CPT_GNOSISDAO)

    def _decode_redemption_claim(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode the payout of the pro-rata share of the treasury to a redeeming user"""
        if context.tx_log.topics[0] != CLAIMED_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        account = bytes_to_address(context.tx_log.topics[1])
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.location_label == account and
                    event.address == GNOSISDAO_TREASURY_SAFE
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_GNOSISDAO
                event.notes = f'Claim {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} from the GnosisDAO treasury redemption'  # noqa: E501

        return EvmDecodingOutput(matched_counterparty=CPT_GNOSISDAO)

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            REDEMPTION_DEPOSIT_ADDRESS: (self._decode_redemption_deposit,),
            REDEMPTION_DISTRIBUTOR_ADDRESS: (self._decode_redemption_claim,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (GNOSISDAO_CPT_DETAILS,)
