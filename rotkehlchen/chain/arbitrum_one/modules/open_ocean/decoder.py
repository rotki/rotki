import logging
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.evm.decoding.open_ocean.constants import CPT_OPENOCEAN
from rotkehlchen.chain.evm.decoding.open_ocean.decoder import (
    OpenOceanDecoder as OpenOceanBaseDecoder,
)
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress


DISTRIBUTOR_ADDR: Final = string_to_evm_address('0x6D9e6bdfd17955B8B8A3Fe0e02375e65e3f20d0a')
CLAIMED_REWARDS: Final = b'\xd1\xa3\xbek\xab\xc4\xd8\xa7\x9e\x04\xc6rt\xc6\x11-\xe4\xbf\xb1\x1a\xf5\xf3e\x8a\x13\xdd\xf0a\xc4\xe3\xd8`'  # noqa: E501

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OpenOceanDecoder(OpenOceanBaseDecoder):

    def _process_arb_airdrop(self, context: 'DecoderContext') -> 'EvmDecodingOutput':
        """This logic processes an airdrop made from the OpenOcean team as part of the
        swaps incentive program using the ARB granted by the Arbitrum DAO
        https://forum.arbitrum.foundation/t/openocean-final-stip-round-1/17564/1
        """
        if context.tx_log.topics[0] != CLAIMED_REWARDS:
            return DEFAULT_EVM_DECODING_OUTPUT

        amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[64:96]),
            token=(token := self.base.get_or_create_evm_token(
                address=bytes_to_address(context.tx_log.data[96:128]),
            )),
        )

        for event in context.decoded_events:
            if (
                event.address == DISTRIBUTOR_ADDR and
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == amount and
                event.asset == token
            ):
                event.event_subtype = HistoryEventSubType.REWARD
                event.notes = f'Receive {event.amount} {token.symbol} from OpenOcean as part of activity incentives'  # noqa: E501
                event.counterparty = CPT_OPENOCEAN
                break
        else:
            log.error(f'Failed to match distributor reward in {context.transaction}')

        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return super().addresses_to_decoders() | {DISTRIBUTOR_ADDR: (self._process_arb_airdrop,)}
