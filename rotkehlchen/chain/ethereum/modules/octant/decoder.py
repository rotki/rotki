import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import (
    token_normalized_value,
    token_normalized_value_decimals,
)
from rotkehlchen.chain.evm.constants import WITHDRAWN_TOPIC
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.constants.assets import A_ETH, A_GLM
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_OCTANT, LOCKED, OCTANT_DEPOSITS, OCTANT_REWARDS, UNLOCKED

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OctantDecoder(DecoderInterface):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.glm = A_GLM.resolve_to_evm_token()

    def _decode_locker_events(self, context: DecoderContext) -> DecodingOutput:
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

        raw_amount = int.from_bytes(context.tx_log.data[32:64])
        address = bytes_to_address(context.tx_log.data[96:128])
        if self.base.is_tracked(address) is False:
            return DEFAULT_DECODING_OUTPUT

        amount = token_normalized_value(raw_amount, self.glm)

        for event in context.decoded_events:
            if (
                    event.event_type == expected_type and
                    event.asset == self.glm and
                    event.address == OCTANT_DEPOSITS and
                    event.amount == amount
            ):
                event.event_type = new_type
                event.event_subtype = new_subtype
                event.counterparty = CPT_OCTANT
                event.notes = f'{verb} {event.amount} GLM {preposition} Octant'
                event.sequence_index = context.tx_log.log_index + 1  # push it after approval if any  # noqa: E501
                break
        else:
            log.error(f'Could not find corresponding GLM transfer for Octant {verb} at: {context.transaction.tx_hash.hex()}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_reward_events(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != WITHDRAWN_TOPIC:
            return DEFAULT_DECODING_OUTPUT

        user = bytes_to_address(context.tx_log.data[0:32])
        if not self.base.is_tracked(user):
            return DEFAULT_DECODING_OUTPUT

        raw_amount = int.from_bytes(context.tx_log.data[32:64])
        epoch = int.from_bytes(context.tx_log.data[64:96])
        amount = token_normalized_value_decimals(raw_amount, 18)  # always ETH
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.asset == A_ETH and
                    event.location_label == user and
                    event.amount == amount
            ):
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_OCTANT
                event.notes = f'Claim {event.amount} ETH as Octant epoch {epoch} reward'
                break
        else:
            log.error(f'Could not find corresponding ETH receive transaction for Octant rewards withdrawal at: {context.transaction.tx_hash.hex()}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            OCTANT_DEPOSITS: (self._decode_locker_events,),
            OCTANT_REWARDS: (self._decode_reward_events,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_OCTANT,
            label='Octant',
            image='octant.svg',
        ),)
