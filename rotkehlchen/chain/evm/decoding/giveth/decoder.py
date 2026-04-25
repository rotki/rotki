import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import asset_normalized_value, token_normalized_value_decimals
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS, SIMPLE_CLAIM
from rotkehlchen.chain.evm.decoding.giveth.constants import (
    CPT_DETAILS_GIVETH,
    CPT_GIVETH,
    DONATION_MADE_TOPIC,
)
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import get_donation_event_params
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


class GivethDonationDecoderBase(EvmDecoderInterface):
    """Decoder for Giveth's multi-donate contract (donateManyETH / donateManyERC20).

    A separate DonationMade event is emitted per recipient, so each event maps 1:1
    to a transfer that needs to be marked as a Giveth donation.
    """

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            donation_contract_address: 'ChecksumEvmAddress',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.donation_contract_address = donation_contract_address

    def _decode_donation_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != DONATION_MADE_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        sender_tracked = self.base.is_tracked(sender_address := context.transaction.from_address)
        recipient_tracked = self.base.is_tracked(recipient_address := bytes_to_address(context.tx_log.topics[1]))  # noqa: E501
        if not sender_tracked and not recipient_tracked:
            return DEFAULT_EVM_DECODING_OUTPUT

        amount_received = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[:32]),
            asset=(token_received := self.base.get_token_or_native(bytes_to_address(context.tx_log.topics[2]))),  # noqa: E501
        )
        new_type, expected_type, _, _, notes = get_donation_event_params(
            context=context,
            sender_address=sender_address,
            recipient_address=recipient_address,
            sender_tracked=sender_tracked,
            recipient_tracked=recipient_tracked,
            asset=token_received,
            amount=amount_received,
            payer_address=sender_address,
            counterparty=CPT_GIVETH,
        )
        for event in context.decoded_events:
            if (
                    event.event_type == expected_type and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == token_received and
                    event.amount == amount_received
            ):
                event.event_type = new_type
                event.counterparty = CPT_GIVETH
                event.event_subtype = HistoryEventSubType.DONATE
                event.notes = notes
                break
        else:
            log.error(f'Failed to find giveth donation event in {context.transaction}')

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return {self.donation_contract_address: (self._decode_donation_events,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CPT_DETAILS_GIVETH,)


class GivethDecoderBase(GivethDonationDecoderBase, ABC):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            distro_address: 'ChecksumEvmAddress',
            givpower_staking_address: 'ChecksumEvmAddress',
            donation_contract_address: 'ChecksumEvmAddress',
            giv_token_id: str,
            pow_token_id: str,

    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            donation_contract_address=donation_contract_address,
        )
        self.giv_token_id = giv_token_id
        self.pow_token_id = pow_token_id
        self.distro_address = distro_address
        self.givpower_staking_address = givpower_staking_address

    def _decode_token_locked(self, context: DecoderContext) -> EvmDecodingOutput:
        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

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
        return EvmDecodingOutput(events=[lock_event])

    def decode_claim(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != SIMPLE_CLAIM or not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1])):  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

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

        return DEFAULT_EVM_DECODING_OUTPUT

    @abstractmethod
    def decode_staking_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """The staking events are slightly different in gnosis and optimism so let
        each decoder implement them"""

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return super().addresses_to_decoders() | {
            self.distro_address: (self.decode_claim,),
            self.givpower_staking_address: (self.decode_staking_events,),
        }
