import logging
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.decoding.constants import STAKED, WITHDRAWN
from rotkehlchen.chain.evm.decoding.giveth.constants import (
    CPT_GIVETH,
    TOKEN_LOCKED,
)
from rotkehlchen.chain.evm.decoding.giveth.decoder import GivethDecoderBase
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.gnosis.modules.giveth.constants import (
    GGIV_TOKEN_ID,
    GIV_TOKEN_ID,
    GIVPOW_ADDRESS,
    GNOSIS_GIVPOWERSTAKING_WRAPPER,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GivethDecoder(GivethDecoderBase):

    def __init__(  # pylint: disable=super-init-not-called
            self,
            evm_inquirer: 'GnosisInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            distro_address=string_to_evm_address('0xc0dbDcA66a0636236fAbe1B3C16B1bD4C84bB1E1'),
            givpower_staking_address=GIVPOW_ADDRESS,
            giv_token_id=GIV_TOKEN_ID,
            pow_token_id='eip155:100/erc20:0xD93d3bDBa18ebcB3317a57119ea44ed2Cf41C2F2',
        )

    def decode_staking_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == STAKED:
            return self._decode_deposit(context=context)
        elif context.tx_log.topics[0] == WITHDRAWN:
            return self._decode_withdraw(context=context)
        elif context.tx_log.topics[0] == TOKEN_LOCKED:
            return self._decode_token_locked(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_deposit(self, context: DecoderContext) -> EvmDecodingOutput:
        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # GIV has 18 decimals
        )
        out_event = None
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.asset.identifier == self.giv_token_id and
                    event.address == GNOSIS_GIVPOWERSTAKING_WRAPPER and
                    amount == event.amount
            ):
                out_event = event
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.counterparty = CPT_GIVETH
                event.notes = f'Deposit {amount} GIV for staking'
                break
        else:
            log.error(f'Could not find the GIV/PoW token transfers for {context.transaction}')
            return DEFAULT_EVM_DECODING_OUTPUT

        # Since the receive transaction comes after we need an action item
        action_items = [ActionItem(
            action='transform',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            amount=amount,
            location_label=user,
            asset=Asset(self.pow_token_id),
            to_event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            to_location_label=user,
            to_address=context.tx_log.address,
            to_notes='Receive {amount} POW after depositing GIV',  # to be filled by the action item  # noqa: E501
            to_counterparty=CPT_GIVETH,
            paired_events_data=([out_event], True),  # make sure order is respected
        ), ActionItem(  # also make an action item to skip ggiv
            action='skip',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            amount=amount,
            location_label=user,
            asset=Asset(GGIV_TOKEN_ID),
        )]
        return EvmDecodingOutput(action_items=action_items)

    def _decode_withdraw(self, context: DecoderContext) -> EvmDecodingOutput:
        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # GIV has 18 decimals
        )
        action_items = [ActionItem(  # transform the returning of givpow
            action='transform',
            from_event_type=HistoryEventType.SPEND,
            from_event_subtype=HistoryEventSubType.NONE,
            amount=amount,
            location_label=user,
            asset=Asset(self.pow_token_id),
            to_event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            to_address=context.tx_log.address,
            to_notes='Return {amount} POW to Giveth staking',  # to be filled by the action item
            to_counterparty=CPT_GIVETH,
            pair_with_next_action_item=True,
         ), ActionItem(  # transform the receival of GIV
             action='transform',
             from_event_type=HistoryEventType.RECEIVE,
             from_event_subtype=HistoryEventSubType.NONE,
             amount=amount,
             location_label=user,
             asset=Asset(self.giv_token_id),
             to_event_type=HistoryEventType.WITHDRAWAL,
             to_event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
             to_notes='Withdraw {amount} GIV from staking',  # to be filled by the action item
             to_counterparty=CPT_GIVETH,
         ), ActionItem(  # also make an action item to skip ggiv
             action='skip',
             from_event_type=HistoryEventType.SPEND,
             from_event_subtype=HistoryEventSubType.NONE,
             amount=amount,
             location_label=user,
             asset=Asset(GGIV_TOKEN_ID),
         )]
        return EvmDecodingOutput(action_items=action_items)
