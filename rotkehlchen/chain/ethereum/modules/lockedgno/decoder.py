import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress

from .constants import CPT_LOCKEDGNO, LOCKED_GNO_ADDRESS

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class LockedgnoDecoder(EvmDecoderInterface):

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
        self.gno = get_or_create_evm_token(
            userdb=self.base.database,
            evm_address=string_to_evm_address('0x6810e776880C02933D47DB1b9fc05908e5386b96'),
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=ethereum_inquirer,
        )
        self.lgno = get_or_create_evm_token(
            userdb=self.base.database,
            evm_address=string_to_evm_address('0x4f8AD938eBA0CD19155a835f617317a6E788c868'),
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=ethereum_inquirer,
        )

    def _decode_events(self, context: DecoderContext) -> EvmDecodingOutput:
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.asset == self.gno and
                    event.address == LOCKED_GNO_ADDRESS
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.counterparty = CPT_LOCKEDGNO
                event.notes = f'Deposit {event.amount} GNO to the locking contract'

                # also create an action item for the receive of the locked gno tokens.
                # Funny thing is that the log shows transfer from the user to the contract
                # though it's the other way around in reality.
                action_item = ActionItem(
                    action='transform',
                    from_event_type=HistoryEventType.SPEND,
                    from_event_subtype=HistoryEventSubType.NONE,
                    asset=self.lgno,
                    amount=event.amount,
                    to_event_type=HistoryEventType.RECEIVE,
                    to_event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                    to_notes=f'Receive {event.amount} locked GNO from the locking contract',
                    to_counterparty=CPT_LOCKEDGNO,
                )
                return EvmDecodingOutput(action_items=[action_item])

            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.asset == self.gno and
                    event.address == LOCKED_GNO_ADDRESS
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.counterparty = CPT_LOCKEDGNO
                event.notes = f'Receive {event.amount} GNO back from the locking contract'

                # also create an action item for the returning of the locked gno tokens.
                # Funny thing is that the log shows transfer from the contract to the user
                # though it's the other way around in reality.
                action_item = ActionItem(
                    action='transform',
                    from_event_type=HistoryEventType.RECEIVE,
                    from_event_subtype=HistoryEventSubType.NONE,
                    asset=self.lgno,
                    amount=event.amount,
                    to_event_type=HistoryEventType.SPEND,
                    to_event_subtype=HistoryEventSubType.RETURN_WRAPPED,
                    to_notes=f'Return {event.amount} locked GNO to the locking contract',
                    to_counterparty=CPT_LOCKEDGNO,
                )
                return EvmDecodingOutput(action_items=[action_item])

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {LOCKED_GNO_ADDRESS: (self._decode_events,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_LOCKEDGNO,
            label='Locked GNO',
            image='gnosis.svg',
        ),)
