from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.chain.arbitrum_one.decoding.interfaces import ArbitrumDecoderInterface
from rotkehlchen.chain.arbitrum_one.modules.umami.constants import (
    CPT_UMAMI,
    UMAMI_STAKING_CONTRACT,
)
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

DEPOSIT_TOPIC: Final = b'\xdc\xbc\x1c\x05$\x0f1\xff:\xd0g\xef\x1e\xe3\\\xe4\x99wbu.:\tR\x84uED\xf4\xc7\t\xd7'  # noqa: E501
TRANSFER_TOPIC: Final = b'\xdd\xf2R\xad\x1b\xe2\xc8\x9bi\xc2\xb0h\xfc7\x8d\xaa\x95+\xa7\xf1c\xc4\xa1\x16(\xf5ZM\xf5#\xb3\xef'  # noqa: E501
WITHDRAW_TOPIC: Final = b'\xfb\xdey} \x1ch\x1b\x91\x05e)\x11\x9e\x0b\x02@|{\xb9jJ,u\xc0\x1f\xc9fr2\xc8\xdb'  # noqa: E501
STAKE_TOPIC: Final = b'\x90\x89\x08\t\xc6T\xf1\x1dnr\xa2\x8f\xa6\x01Iw\n\r\x11\xecl\x921\x9dl\xeb+\xb0\xa4\xea\x1a\x15'  # noqa: E501
UNSTAKE_TOPIC: Final = b'\xf2y\xe6\xa1\xf5\xe3 \xcc\xa9\x115gm\x9c\xb6\xe4L\xa8\xa0\x8c\x0b\x884+\xcd\xb1\x14Oe\x11\xb5h'  # noqa: E501
REWARD_TOPIC: Final = b'q\xba\xb6\\\xed.WPwZ\x06\x13\xbe\x06}\xf4\x8e\xf0l\xf9*In\xbfvc\xae\x06`\x92IT'  # noqa: E501
DEPOSIT_EXECUTION_FOUR_BYTES: Final = b'\xdb\x10\xc3\xb9'


class FoundEventType(Enum):
    MAIN = auto()
    FEE = auto()
    NONE = auto()


class UmamiDecoder(ArbitrumDecoderInterface):
    def __init__(
            self,
            evm_inquirer: 'ArbitrumOneInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )

    def _decode_deposit_withdraw_request(
            self,
            event: 'EvmEvent',
            match_amount: 'FVal',
            event_type: 'HistoryEventType',
            event_subtype: 'HistoryEventSubType',
            event_notes: str,
            fee_match_amount: 'FVal',
            fee_event_type: 'HistoryEventType',
    ) -> FoundEventType:
        """Decode a deposit/withdraw request event and its corresponding execution cost event.
        These two events are very similar, and must be differentiated by matching their
        balances against the values recorded elsewhere in the context.

        Returns FoundEventType identifying the type of event found to allow reshuffling later.
        """
        if event.amount == match_amount:
            event.event_type = event_type
            event.event_subtype = event_subtype
            event.notes = event_notes
            event.counterparty = CPT_UMAMI
            return FoundEventType.MAIN
        elif event.amount == fee_match_amount:
            event.event_type = fee_event_type
            event.event_subtype = HistoryEventSubType.FEE
            event.notes = f'Spend {event.amount} ETH as Umami execution fee'
            event.counterparty = CPT_UMAMI
            return FoundEventType.FEE

        return FoundEventType.NONE

    def _decode_deposit_request(self, context: DecoderContext, event: 'EvmEvent') -> FoundEventType:  # noqa: E501
        """Decode deposit request events.
        Returns FoundEventType identifying the type of event found to allow reshuffling later.
        """
        resolved_asset = event.asset.resolve_to_crypto_asset()
        match_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[0:32]),
            asset=resolved_asset,
        )
        return self._decode_deposit_withdraw_request(
            event=event,
            match_amount=match_amount,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            event_notes=f'Deposit {match_amount} {resolved_asset.symbol} into Umami',
            fee_match_amount=asset_normalized_value(
                amount=context.transaction.value,
                asset=resolved_asset,
            ),
            fee_event_type=HistoryEventType.DEPOSIT,
        )

    def _decode_withdraw_request(self, context: DecoderContext, event: 'EvmEvent') -> FoundEventType:  # noqa: E501
        """Decode withdraw request events.
        Returns FoundEventType identifying the type of event found to allow reshuffling later.
        """
        resolved_asset = event.asset.resolve_to_crypto_asset()
        match_amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[32:64]),
            asset=resolved_asset,
        )
        return self._decode_deposit_withdraw_request(
            event=event,
            match_amount=match_amount,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            event_notes=f'Return {match_amount} {resolved_asset.symbol} to Umami',
            fee_match_amount=asset_normalized_value(
                amount=context.transaction.value,
                asset=resolved_asset,
            ),
            fee_event_type=HistoryEventType.WITHDRAWAL,
        )

    def _decode_umami_vault_events(self, context: DecoderContext) -> DecodingOutput:
        """Decode umami vault deposit/withdraw events.

        A deposit/withdraw consists of two transactions, a request tx and an execution tx.
        The event for deposit execution is not available in decoded_events here,
        and must be transformed later via an ActionItem.
        """
        main_event, fee_event = None, None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE
            ):  # deposit or withdraw request
                type_found = FoundEventType.NONE
                if context.tx_log.topics[0] == DEPOSIT_TOPIC:
                    type_found = self._decode_deposit_request(context=context, event=event)
                elif context.tx_log.topics[0] == WITHDRAW_TOPIC:
                    type_found = self._decode_withdraw_request(context=context, event=event)

                if type_found == FoundEventType.MAIN:
                    main_event = event
                elif type_found == FoundEventType.FEE:
                    fee_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                context.tx_log.topics[0] == TRANSFER_TOPIC
            ):  # withdraw execution
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.notes = f'Withdraw {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} from Umami'  # noqa: E501
                event.counterparty = CPT_UMAMI
                main_event = event

        if main_event is not None:
            maybe_reshuffle_events(
                ordered_events=[main_event, fee_event],
                events_list=context.decoded_events,
            )
            return DEFAULT_DECODING_OUTPUT

        if (
            context.tx_log.topics[0] == TRANSFER_TOPIC and
            context.transaction.input_data.startswith(DEPOSIT_EXECUTION_FOUR_BYTES)
        ):  # deposit execution
            vault_asset = self.base.get_or_create_evm_asset(context.tx_log.address)
            receive_amount = asset_normalized_value(
                amount=int.from_bytes(context.tx_log.data[0:32]),
                asset=vault_asset,
            )
            return DecodingOutput(action_items=[ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=vault_asset,
                amount=receive_amount,
                to_event_type=HistoryEventType.RECEIVE,
                to_event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                to_counterparty=CPT_UMAMI,
                to_notes=f'Receive {receive_amount} {vault_asset.symbol} after a deposit in Umami',
            )])

        return DEFAULT_DECODING_OUTPUT

    def _decode_umami_staking_events(self, context: DecoderContext) -> DecodingOutput:
        """Decode stake/unstake/reward events."""
        for event in context.decoded_events:
            asset_symbol = event.asset.resolve_to_asset_with_symbol().symbol
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                context.tx_log.topics[0] == STAKE_TOPIC
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_UMAMI
                event.notes = f'Stake {event.amount} {asset_symbol} in Umami'
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                if context.tx_log.topics[0] == REWARD_TOPIC:
                    event.event_type = HistoryEventType.STAKING
                    event.event_subtype = HistoryEventSubType.REWARD
                    event.counterparty = CPT_UMAMI
                    event.notes = f'Receive staking reward of {event.amount} {asset_symbol} from Umami'  # noqa: E501
                elif context.tx_log.topics[0] == UNSTAKE_TOPIC:
                    event.event_type = HistoryEventType.STAKING
                    event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                    event.counterparty = CPT_UMAMI
                    event.notes = f'Unstake {event.amount} {asset_symbol} from Umami'

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            token.evm_address: (self._decode_umami_vault_events,)
            for token in GlobalDBHandler.get_evm_tokens(
                    chain_id=self.evm_inquirer.chain_id,
                    protocol=CPT_UMAMI,
            )
        } | {UMAMI_STAKING_CONTRACT: (self._decode_umami_staking_events,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_UMAMI, label='Umami', image='umami.svg'),)
