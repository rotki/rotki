import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS, SIMPLE_CLAIM
from rotkehlchen.chain.evm.decoding.giveth.constants import CPT_DETAILS_GIVETH, CPT_GIVETH
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GivethDecoderBase(EvmDecoderInterface, ABC):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            distro_address: 'ChecksumEvmAddress',
            givpower_staking_address: 'ChecksumEvmAddress',
            giv_token_id: str,
            pow_token_id: str,

    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.giv_token_id = giv_token_id
        self.pow_token_id = pow_token_id
        self.distro_address = distro_address
        self.givpower_staking_address = givpower_staking_address

    def _decode_token_locked(self, context: DecoderContext) -> DecodingOutput:
        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # GIV has 18 decimals
        )
        rounds = int.from_bytes(context.tx_log.data[32:64])

        lock_event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset(self.giv_token_id),
            amount=amount,
            location_label=user,
            notes=f'Lock {amount} GIV for {rounds} round/s',
            address=context.tx_log.address,
            counterparty=CPT_GIVETH,
        )
        receive_event = None
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.asset.identifier == self.pow_token_id and
                    event.location_label == user
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = CPT_GIVETH
                event.notes = f'Receive {event.amount} POW after locking GIV'
                receive_event = event
                break

        else:
            log.error(f'Could not find the GivPoW token transfer after locking GIV for {context.transaction}')  # noqa: E501

        maybe_reshuffle_events(
            ordered_events=[lock_event, receive_event],
            events_list=context.decoded_events,
        )
        return DecodingOutput(events=[lock_event])

    def decode_claim(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != SIMPLE_CLAIM or not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1])):  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # GIV has 18 decimals
        )
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.asset.identifier == self.giv_token_id and
                    event.location_label == user and
                    amount == event.amount
            ):
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_GIVETH
                event.notes = f'Claim {amount} GIV'
                break
        else:
            log.error(f'Could not find the Giv token transfer after reward claiming for {context.transaction}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    @abstractmethod
    def decode_staking_events(self, context: DecoderContext) -> DecodingOutput:
        """The staking events are slightly different in gnosis and optimism so let
        each decoder implement them"""

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return {
            self.distro_address: (self.decode_claim,),
            self.givpower_staking_address: (self.decode_staking_events,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CPT_DETAILS_GIVETH,)
