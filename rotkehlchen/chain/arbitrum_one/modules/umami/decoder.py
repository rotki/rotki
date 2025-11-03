from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.arbitrum_one.decoding.interfaces import ArbitrumDecoderInterface
from rotkehlchen.chain.arbitrum_one.modules.umami.constants import (
    CPT_UMAMI,
    UMAMI_STAKING_CONTRACT,
)
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import (
    DEPOSIT_TOPIC,
    STAKE_TOPIC,
    UNSTAKE_TOPIC,
    WITHDRAW_TOPIC_V3,
)
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

REWARD_TOPIC: Final = b'q\xba\xb6\\\xed.WPwZ\x06\x13\xbe\x06}\xf4\x8e\xf0l\xf9*In\xbfvc\xae\x06`\x92IT'  # noqa: E501
DEPOSIT_EXECUTION_FOUR_BYTES: Final = b'\xdb\x10\xc3\xb9'
UMAMI_DEPOSIT_WITHDRAWAL_FEE_PERCENTAGE: Final = FVal('0.0015')  # this is an estimate since the actual percentage is dynamic -- 0.15%  # noqa: E501


class FoundEventType(Enum):
    MAIN = auto()
    FEE = auto()
    NONE = auto()


class UmamiDecoder(ArbitrumDecoderInterface):
    def __init__(
            self,
            evm_inquirer: 'ArbitrumOneInquirer',
            base_tools: 'BaseEvmDecoderTools',
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

    def _decode_umami_vault_events(self, context: DecoderContext) -> EvmDecodingOutput:
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
                elif context.tx_log.topics[0] == WITHDRAW_TOPIC_V3:
                    type_found = self._decode_withdraw_request(context=context, event=event)

                if type_found == FoundEventType.MAIN:
                    main_event = event
                elif type_found == FoundEventType.FEE:
                    fee_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                context.tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER
            ):  # withdraw execution
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.notes = f'Withdraw {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} from Umami'  # noqa: E501
                event.counterparty = CPT_UMAMI
                main_event = event

        if main_event is not None:
            protocol_fee: FVal | None = None
            if (
                    main_event.event_type == HistoryEventType.DEPOSIT and
                    main_event.event_subtype == HistoryEventSubType.DEPOSIT_FOR_WRAPPED
            ):
                protocol_fee = UMAMI_DEPOSIT_WITHDRAWAL_FEE_PERCENTAGE * main_event.amount
                main_event.amount -= protocol_fee
                # Use resolve_to_crypto_asset() here and below to leverage the
                # previously cached result and avoid additional database query
                main_event.asset = main_event.asset.resolve_to_crypto_asset()
                main_event.notes = f'Deposit {main_event.amount} {main_event.asset.symbol} into Umami'  # noqa: E501
            elif (
                    main_event.event_type == HistoryEventType.WITHDRAWAL and
                    main_event.event_subtype == HistoryEventSubType.REDEEM_WRAPPED
            ):
                protocol_fee = UMAMI_DEPOSIT_WITHDRAWAL_FEE_PERCENTAGE * main_event.amount
                main_event.amount += protocol_fee
                main_event.asset = main_event.asset.resolve_to_crypto_asset()
                main_event.notes = f'Withdraw {main_event.amount} {main_event.asset.symbol} from Umami'  # noqa: E501

            ordered_events = [main_event, fee_event]
            if protocol_fee is not None:
                protocol_fee_event = self.base.make_event_from_transaction(
                    transaction=context.transaction,
                    tx_log=context.tx_log,
                    event_type=main_event.event_type,
                    event_subtype=HistoryEventSubType.FEE,
                    asset=main_event.asset,
                    notes=f'Spend {protocol_fee} {main_event.asset.symbol} as Umami protocol fee',  # type: ignore[attr-defined]  # it has been resolved to crypto asset above
                    amount=protocol_fee,
                    address=main_event.address,
                    counterparty=CPT_UMAMI,
                    location_label=main_event.location_label,
                )
                ordered_events.insert(1, protocol_fee_event)
                context.decoded_events.append(protocol_fee_event)

            maybe_reshuffle_events(
                ordered_events=ordered_events,
                events_list=context.decoded_events,
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        if (
            context.tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
            context.transaction.input_data.startswith(DEPOSIT_EXECUTION_FOUR_BYTES)
        ):  # deposit execution
            vault_asset = self.base.get_or_create_evm_asset(context.tx_log.address)
            receive_amount = asset_normalized_value(
                amount=int.from_bytes(context.tx_log.data[0:32]),
                asset=vault_asset,
            )
            return EvmDecodingOutput(action_items=[ActionItem(
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

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_umami_staking_events(self, context: DecoderContext) -> EvmDecodingOutput:
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

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            token.evm_address: (self._decode_umami_vault_events,)
            for token in GlobalDBHandler.get_evm_tokens(
                    chain_id=self.node_inquirer.chain_id,
                    protocol=CPT_UMAMI,
            )
        } | {UMAMI_STAKING_CONTRACT: (self._decode_umami_staking_events,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_UMAMI, label='Umami', image='umami.svg'),)
