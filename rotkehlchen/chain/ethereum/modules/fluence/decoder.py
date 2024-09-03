import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import CLAIMED, CPT_FLUENCE, DEV_REWARD_DISTRIBUTOR, FLUENCE_IDENTIFIER

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class FluenceDecoder(DecoderInterface):

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

    def _decode_fluence_claim(
            self,
            context: DecoderContext,
            user_address: ChecksumEvmAddress,
    ) -> DecodingOutput:
        amount = token_normalized_value_decimals(hex_or_bytes_to_int(context.tx_log.data[32:64]), 18)  # noqa: E501

        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.balance.amount == amount and event.location_label == user_address and event.asset.identifier == ethaddress_to_identifier(DEV_REWARD_DISTRIBUTOR):  # noqa: E501
                event.notes = f'Claim {event.balance.amount} FLT-DROP from Fluence dev rewards'
                event.counterparty = CPT_FLUENCE
                event.address = DEV_REWARD_DISTRIBUTOR
                break

        else:
            log.error(f'Could not find the FLT-drop transfer in {context.transaction.tx_hash.hex()}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_fluence_swap_claim(
            self,
            context: DecoderContext,
            user_address: ChecksumEvmAddress,
    ) -> DecodingOutput:
        amount = token_normalized_value_decimals(hex_or_bytes_to_int(context.tx_log.data[0:32]), 18)  # noqa: E501
        # need to also create the FLT-DROP burn event
        out_event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=self.base.get_or_create_evm_token(DEV_REWARD_DISTRIBUTOR),
            balance=Balance(amount=amount),
            location_label=user_address,
            notes=f'Burn {amount} FLT-DROP',
            address=context.tx_log.address,
            counterparty=CPT_FLUENCE,
        )

        in_event = None
        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.balance.amount == amount and event.location_label == user_address and event.asset.identifier == FLUENCE_IDENTIFIER:  # noqa: E501
                event.notes = f'Claim {event.balance.amount} FLT by burning FLT-DROP'
                event.counterparty = CPT_FLUENCE
                event.address = DEV_REWARD_DISTRIBUTOR
                event.event_subtype = HistoryEventSubType.AIRDROP
                in_event = event
                break

        else:
            log.error(f'Could not find the FLT transfer in {context.transaction.tx_hash.hex()}')

        maybe_reshuffle_events(  # Make sure that the out event comes first
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return DecodingOutput(event=out_event)

    def _decode_events(self, context: DecoderContext) -> DecodingOutput:
        if (
            context.tx_log.topics[0] == CLAIMED and
            self.base.is_tracked(user_address := hex_or_bytes_to_address(context.tx_log.data[0:32]))  # noqa: E501
        ):
            return self._decode_fluence_claim(context=context, user_address=user_address)
        elif (
                context.tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                self.base.is_tracked(user_address := hex_or_bytes_to_address(context.tx_log.topics[1])) and  # from # noqa: E501
                hex_or_bytes_to_address(context.tx_log.topics[2]) == ZERO_ADDRESS  # to
        ):
            return self._decode_fluence_swap_claim(context, user_address)

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            DEV_REWARD_DISTRIBUTOR: (self._decode_events,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_FLUENCE, label='Fluence', image='fluence.png'),)
