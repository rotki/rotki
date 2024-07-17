import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import (
    CLAIMED_VESTING,
    CPT_SAFE,
    LOCKED,
    SAFE_LOCKING,
    SAFE_VESTING,
    UNLOCKED,
    WITHDRAWN,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SafeDecoder(DecoderInterface):
    """Decoder for ethereum mainnet safe (mostly token) related activities"""

    def __init__(  # pylint: disable=super-init-not-called
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',  # pylint: disable=unused-argument
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.safe_token = EvmToken('eip155:1/erc20:0x5aFE3855358E112B5647B952709E6165e1c1eEEe')

    def _decode_safe_vesting(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != CLAIMED_VESTING:
            return DEFAULT_DECODING_OUTPUT

        account = hex_or_bytes_to_address(context.tx_log.topics[2])
        beneficiary = hex_or_bytes_to_address(context.tx_log.topics[3])
        if not self.base.any_tracked((account, beneficiary)):
            return DEFAULT_DECODING_OUTPUT

        notes = 'Claim {amount} SAFE from vesting'  # amount set at actionitem process
        if account != beneficiary:
            notes += f' and send to {beneficiary}'
        return DecodingOutput(
            action_items=[ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=self.safe_token,
                to_notes=notes,
                to_counterparty=CPT_SAFE,
                to_address=SAFE_VESTING,
            )],
        )

    def _decode_safe_locked(self, context: DecoderContext) -> DecodingOutput:
        if not self.base.is_tracked(holder := hex_or_bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=hex_or_bytes_to_int(context.tx_log.data[0:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.location_label == holder and
                    event.asset == self.safe_token and
                    event.balance.amount == amount
            ):

                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_SAFE
                event.notes = f'Lock {amount} SAFE for Safe{{Pass}}'
                break

        else:  # transfer not found
            log.error(f'Could not find the transfer of SAFE to the locker for {context.transaction.tx_hash.hex()}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_safe_unlocked(self, context: DecoderContext) -> DecodingOutput:
        if not self.base.is_tracked(holder := hex_or_bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=hex_or_bytes_to_int(context.tx_log.data[0:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=self.safe_token,
            balance=Balance(amount=amount),
            location_label=holder,
            notes=f'Start unlock of {amount} SAFE from Safe{{Pass}}',
            address=context.tx_log.address,
            counterparty=CPT_SAFE,
        )
        return DecodingOutput(event=event)

    def _decode_safe_withdrawn(self, context: DecoderContext) -> DecodingOutput:
        if not self.base.is_tracked(holder := hex_or_bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=hex_or_bytes_to_int(context.tx_log.data[0:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        action_item = ActionItem(
            action='transform',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            location_label=holder,
            asset=self.safe_token,
            amount=amount,
            to_event_type=HistoryEventType.WITHDRAWAL,
            to_event_subtype=HistoryEventSubType.REMOVE_ASSET,
            to_notes=f'Withdraw {amount} SAFE from Safe{{Pass}} locking',
            to_counterparty=CPT_SAFE,
        )
        return DecodingOutput(action_items=[action_item])

    def _decode_safe_locker(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == LOCKED:
            return self._decode_safe_locked(context)
        elif context.tx_log.topics[0] == UNLOCKED:
            return self._decode_safe_unlocked(context)
        elif context.tx_log.topics[0] == WITHDRAWN:
            return self._decode_safe_withdrawn(context)

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            SAFE_VESTING: (self._decode_safe_vesting,),
            SAFE_LOCKING: (self._decode_safe_locker,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_SAFE,
            label='Safe',
            image='safemultisig.svg',
        ),)
