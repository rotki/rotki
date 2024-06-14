import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.constants.assets import A_ETH, A_STETH
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import from_wei, hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import CPT_LIDO, LIDO_STETH_SUBMITTED, STETH_MAX_ROUND_ERROR_WEI

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class LidoDecoder(DecoderInterface):

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
        self.steth_evm_address = A_STETH.resolve_to_evm_token().evm_address

    def _decode_lido_staking_in_steth(self, context: DecoderContext, sender: ChecksumEvmAddress) -> DecodingOutput:  # noqa: E501
        """Decode the submit of eth to lido contract for obtaining steth in return"""
        amount_raw = hex_or_bytes_to_int(context.tx_log.data[:32])
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
                event.balance.amount == collateral_amount and
                event.event_type == HistoryEventType.SPEND and
                event.location_label == sender
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
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
            return DEFAULT_DECODING_OUTPUT

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

        return DecodingOutput(action_items=action_items, matched_counterparty=CPT_LIDO)

    def _decode_lido_eth_staking_contract(self, context: DecoderContext) -> DecodingOutput:
        """Decode interactions with stETH ans wstETH contracts"""
        if (
            context.tx_log.topics[0] == LIDO_STETH_SUBMITTED and
            self.base.is_tracked(sender := hex_or_bytes_to_address(context.tx_log.topics[1]))
        ):
            return self._decode_lido_staking_in_steth(context=context, sender=sender)
        else:
            return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            self.steth_evm_address: (self._decode_lido_eth_staking_contract,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_LIDO, label='Lido eth', image='lido.svg'),)
