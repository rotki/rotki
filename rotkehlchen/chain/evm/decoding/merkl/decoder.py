import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.constants import REWARD_CLAIMED
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_MERKL, MERKL_DISTRIBUTOR_ADDRESS
from .utils import get_merkl_protocol_for_token

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class MerklDecoder(DecoderInterface):

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

    def _decode_reward_claim(self, context: DecoderContext) -> DecodingOutput:
        """Decode a Merkl reward claim event."""
        if context.tx_log.topics[0] != REWARD_CLAIMED:
            return DEFAULT_DECODING_OUTPUT

        claimed_asset = self.base.get_or_create_evm_asset(
            address=(claimed_asset_addr := bytes_to_address(context.tx_log.topics[2])),
        )
        reward_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[:32]),
            asset=claimed_asset,
        )
        user_address = bytes_to_address(context.tx_log.topics[1])
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == context.tx_log.address and
                event.asset == claimed_asset and
                event.amount == reward_amount
            ):
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_MERKL
                protocol = get_merkl_protocol_for_token(
                    account=user_address,
                    token=claimed_asset_addr,
                    chain_id=self.evm_inquirer.chain_id,
                )
                from_str = f'{protocol} via Merkl' if protocol else 'Merkl'
                event.notes = f'Claim {event.amount} {claimed_asset.symbol} from {from_str}'
                break
        else:
            log.error(f'Failed to find Merkl reward claim event in {context.transaction}')

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {MERKL_DISTRIBUTOR_ADDRESS: (self._decode_reward_claim,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_MERKL,
            label='Merkl',
            image='merkl_light.svg',
            darkmode_image='merkl_dark.svg',
        ),)
