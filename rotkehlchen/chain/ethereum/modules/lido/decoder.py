import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import (
    asset_normalized_value,
    token_normalized_value_decimals,
)
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.constants.assets import A_ETH, A_STETH, A_WSTETH
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address, from_wei

from .constants import (
    CPT_LIDO,
    LIDO_STETH_SUBMITTED,
    LIDO_TRANSFER_SHARES,
    STETH_MAX_ROUND_ERROR_WEI,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class LidoDecoder(EvmDecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.steth_evm_address = A_STETH.resolve_to_evm_token().evm_address
        self.wsteth_evm_address = A_WSTETH.resolve_to_evm_token().evm_address

    def _decode_lido_staking_in_steth(self, context: DecoderContext, sender: ChecksumEvmAddress) -> EvmDecodingOutput:  # noqa: E501
        """Decode the submit of eth to lido contract for obtaining steth in return"""
        amount_raw = int.from_bytes(context.tx_log.data[:32])
        collateral_amount = token_normalized_value_decimals(
            token_amount=amount_raw,
            token_decimals=18,
        )

        # Searching for the already decoded event,
        # containing the ETH transfer of the submit transaction
        paired_event = None
        action_from_event_type = None
        for event in context.decoded_events:
            if (
                event.address == self.steth_evm_address and
                event.asset == A_ETH and
                event.amount == collateral_amount and
                event.event_type == HistoryEventType.SPEND and
                event.location_label == sender
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.notes = f'Submit {collateral_amount} ETH to Lido'
                event.counterparty = CPT_LIDO
                #  preparing next action to be processed when erc20 transfer will be decoded
                #  by rotki needed because submit event is emitted prior to the erc20 transfer
                paired_event = event
                action_from_event_type = HistoryEventType.RECEIVE
                action_to_event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                action_to_notes = 'Receive {amount} stETH in exchange for the deposited ETH'  # {amount} to be set by transform ActionItem  # noqa: E501
                break
        else:  # did not find anything
            log.error(
                f'At lido steth submit decoding of tx {context.transaction.tx_hash.hex()}'
                f' did not find the related ETH transfer',
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        action_items = []  # also create an action item for the reception of the stETH tokens
        if paired_event is not None and action_from_event_type is not None:
            action_items.append(ActionItem(
                action='transform',
                from_event_type=action_from_event_type,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=A_STETH,
                amount=collateral_amount,
                amount_error_tolerance=from_wei(STETH_MAX_ROUND_ERROR_WEI),  # passing the maximum rounding error for finding the related stETH transfer  # noqa: E501
                to_event_subtype=action_to_event_subtype,
                to_notes=action_to_notes,
                to_counterparty=CPT_LIDO,
                paired_events_data=((paired_event,), True),
                extra_data={'staked_eth': str(collateral_amount)},
            ))

        return EvmDecodingOutput(action_items=action_items, matched_counterparty=CPT_LIDO)

    def _decode_deposit_event(self, context: DecoderContext) -> EvmDecodingOutput:
        deposited_shares_raw = int.from_bytes(context.tx_log.data[:32])
        deposited_shares = asset_normalized_value(
            amount=deposited_shares_raw,
            asset=A_WSTETH.resolve_to_crypto_asset(),
        )

        in_event = out_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.amount.is_close(deposited_shares) and
                event.asset == A_WSTETH
            ):
                event.notes = f'Receive {deposited_shares} {A_WSTETH.resolve_to_evm_token().symbol}'  # noqa: E501
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = CPT_LIDO
                event.address = A_WSTETH.resolve_to_evm_token().evm_address
                in_event = event
            if (
                event.event_type == HistoryEventType.SPEND and
                # (event.amount / deposited_shares) < FVal('0.1') and
                event.asset == A_STETH
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.notes = f'Wrap {event.amount} {A_STETH.resolve_to_evm_token().symbol} in {A_WSTETH.resolve_to_evm_token().symbol}'  # noqa: E501
                event.counterparty = CPT_LIDO
                event.address = A_STETH.resolve_to_evm_token().evm_address
                out_event = event

        if out_event is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput()

    def _decode_withdraw_event(self, context: DecoderContext) -> EvmDecodingOutput:
        withdrawn_shares_raw = int.from_bytes(context.tx_log.data[:32])
        withdrawn_shares = asset_normalized_value(
            amount=withdrawn_shares_raw,
            asset=A_WSTETH.resolve_to_crypto_asset(),
        )

        in_event = out_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.amount.is_close(withdrawn_shares) and
                event.asset == A_WSTETH
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.notes = f'Unwrap {event.amount} {A_WSTETH.resolve_to_evm_token().symbol}'
                event.counterparty = CPT_LIDO
                event.address = A_WSTETH.resolve_to_evm_token().evm_address
                out_event = event
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.asset == A_STETH
            ):
                event.notes = f'Receive {event.amount} {A_STETH.resolve_to_evm_token().symbol}'
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.counterparty = CPT_LIDO
                event.address = A_STETH.resolve_to_evm_token().evm_address
                in_event = event

        if out_event is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput()

    def _decode_lido_eth_staking_contract(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode interactions with stETH and wstETH contracts"""
        if (
            context.tx_log.topics[0] == LIDO_STETH_SUBMITTED and
            self.base.is_tracked(sender := bytes_to_address(context.tx_log.topics[1]))
        ):
            return self._decode_lido_staking_in_steth(context=context, sender=sender)
        elif context.tx_log.topics[0] == LIDO_TRANSFER_SHARES:
            from_address = bytes_to_address(context.tx_log.topics[1])
            to_address = bytes_to_address(context.tx_log.topics[2])
            if self.base.is_tracked(from_address) and to_address == self.wsteth_evm_address:
                return self._decode_deposit_event(context)
            elif self.base.is_tracked(to_address) and from_address == self.wsteth_evm_address:
                return self._decode_withdraw_event(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            self.steth_evm_address: (self._decode_lido_eth_staking_contract,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_LIDO, label='Lido eth', image='lido.svg'),)
