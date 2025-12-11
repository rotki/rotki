import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.modules.lido_csm.constants import CPT_LIDO_CSM
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.assets import A_ETH, A_STETH, A_WSTETH
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address, from_wei

from .constants import (
    CPT_LIDO,
    LIDO_STETH_SUBMITTED,
    LIDO_STETH_TRANSFER_SHARES,
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
        self.steth = A_STETH.resolve_to_evm_token()
        self.wsteth = A_WSTETH.resolve_to_evm_token()

    def _decode_lido_staking_in_steth(self, context: DecoderContext, sender: ChecksumEvmAddress) -> EvmDecodingOutput:  # noqa: E501
        """Decode the submit of eth to lido contract for obtaining steth in return"""
        collateral_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=18,
        )

        # Searching for the already decoded event,
        # containing the ETH transfer of the submit transaction
        paired_event = None
        action_from_event_type = None
        for event in context.decoded_events:
            if (
                event.address == self.steth.evm_address and
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
                f'At lido steth submit decoding of tx {context.transaction.tx_hash!s}'
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

    def _decode_steth_wsteth_wrap_unwrap(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes steth/wsteth wrap/unwrap transactions."""
        if self.wsteth.evm_address not in (
            (from_address := bytes_to_address(context.tx_log.topics[1])),
            (to_address := bytes_to_address(context.tx_log.topics[2])),
        ):  # this is just a simple steth transfer instead of a wsteth wrap/unwrap
            return DEFAULT_EVM_DECODING_OUTPUT

        if self.base.is_tracked(user_address := from_address):
            is_wrap = True
            wsteth_expected_event_type = HistoryEventType.RECEIVE
            wsteth_to_event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
            wsteth_to_notes = f'Receive {{amount}} {self.wsteth.symbol} after wrapping'
            steth_expected_event_type = HistoryEventType.SPEND
            steth_to_event_type = HistoryEventType.DEPOSIT
            steth_to_event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
            steth_to_notes = f'Wrap {{amount}} {self.steth.symbol} in {self.wsteth.symbol}'
        elif self.base.is_tracked(user_address := to_address):
            is_wrap = False
            wsteth_expected_event_type = HistoryEventType.SPEND
            wsteth_to_event_subtype = HistoryEventSubType.RETURN_WRAPPED
            wsteth_to_notes = f'Return {{amount}} {self.wsteth.symbol} to be unwrapped'
            steth_expected_event_type = HistoryEventType.RECEIVE
            steth_to_event_type = HistoryEventType.WITHDRAWAL
            steth_to_event_subtype = HistoryEventSubType.REDEEM_WRAPPED
            steth_to_notes = f'Unwrap {{amount}} {self.steth.symbol}'
        else:  # this is a wrap/unwrap for an untracked address
            return DEFAULT_EVM_DECODING_OUTPUT

        wsteth_event, steth_event = None, None
        for event in context.decoded_events:
            if (
                event.event_type == wsteth_expected_event_type and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == self.wsteth and
                event.address == ZERO_ADDRESS and
                event.location_label == user_address
            ):
                event.event_subtype = wsteth_to_event_subtype
                event.counterparty = CPT_LIDO
                event.notes = wsteth_to_notes.format(amount=event.amount)
                wsteth_event = event
            elif (
                event.event_type == steth_expected_event_type and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == self.steth and
                event.address == self.wsteth.evm_address and
                event.location_label == user_address
            ):
                event.event_type = steth_to_event_type
                event.event_subtype = steth_to_event_subtype
                event.counterparty = CPT_LIDO
                event.notes = steth_to_notes.format(amount=event.amount)
                steth_event = event

        if wsteth_event is None or steth_event is None:
            log.error(
                'Failed to find both sides of a Lido steth/wsteth wrap/unwrap '
                f'transaction {context.transaction!s}',
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[steth_event, wsteth_event] if is_wrap else [wsteth_event, steth_event],
            events_list=context.decoded_events,
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_lido_eth_staking_contract(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode interactions with stETH contract"""
        if (
            context.tx_log.topics[0] == LIDO_STETH_SUBMITTED and
            self.base.is_tracked(sender := bytes_to_address(context.tx_log.topics[1]))
        ):
            return self._decode_lido_staking_in_steth(context=context, sender=sender)
        elif context.tx_log.topics[0] == LIDO_STETH_TRANSFER_SHARES:
            return self._decode_steth_wsteth_wrap_unwrap(context=context)
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.steth.evm_address: (self._decode_lido_eth_staking_contract,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (
            CounterpartyDetails(identifier=CPT_LIDO, label='Lido eth', image='lido.svg'),
            CounterpartyDetails(identifier=CPT_LIDO_CSM, label='Lido CSM', image='lido_csm.svg'),
        )
