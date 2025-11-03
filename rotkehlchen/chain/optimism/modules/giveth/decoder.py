import logging
from typing import TYPE_CHECKING, Final

from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.giveth.constants import CPT_GIVETH, TOKEN_LOCKED
from rotkehlchen.chain.evm.decoding.giveth.decoder import GivethDecoderBase
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.modules.giveth.constants import GIV_TOKEN_ID, GIVPOW_ADDRESS
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

TOKEN_DEPOSITED: Final = b'+\xc1}\xef\xafP\xe9\x01\x0bWhY\xc1GB\x1d\n\xafqT^\xe0\xbd\xf6\\J\xea\xfcm\xee\x9c/'  # noqa: E501
DEPOSIT_TOKEN_WITHDRAWN = b'=\x81U\xb4\xc5du\xf1\xae\x1bn\xb3\x11n;\xe1.3V\xca\x00\xa5\x9f\xe0+\x0f\x8c\x80\xe9\x01\xd2\xa7'  # noqa: E501


class GivethDecoder(GivethDecoderBase):

    def __init__(  # pylint: disable=super-init-not-called
            self,
            evm_inquirer: 'OptimismInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            distro_address=string_to_evm_address('0xE3Ac7b3e6B4065f4765d76fDC215606483BF3bD1'),
            givpower_staking_address=GIVPOW_ADDRESS,
            giv_token_id=GIV_TOKEN_ID,
            pow_token_id='eip155:10/erc20:0x301C739CF6bfb6B47A74878BdEB13f92F13Ae5E7',
        )

    def decode_staking_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == TOKEN_DEPOSITED:
            return self._decode_token_movement(
                context=context,
                send_token_id=self.giv_token_id,
                send_type=HistoryEventType.DEPOSIT,
                send_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
                send_to_address=context.tx_log.address,
                send_notes='Deposit {amount} GIV for staking',
                receive_token_id=self.pow_token_id,
                receive_type=HistoryEventType.RECEIVE,
                receive_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                receive_notes='Receive {amount} POW after depositing GIV',
            )
        elif context.tx_log.topics[0] == DEPOSIT_TOKEN_WITHDRAWN:
            return self._decode_token_movement(
                context=context,
                send_token_id=self.pow_token_id,
                send_type=HistoryEventType.SPEND,
                send_subtype=HistoryEventSubType.RETURN_WRAPPED,
                send_to_address=ZERO_ADDRESS,
                send_notes='Return {amount} POW to Giveth staking',
                receive_token_id=self.giv_token_id,
                receive_type=HistoryEventType.WITHDRAWAL,
                receive_subtype=HistoryEventSubType.REDEEM_WRAPPED,
                receive_notes='Withdraw {amount} GIV from staking',
            )
        elif context.tx_log.topics[0] == TOKEN_LOCKED:
            return self._decode_token_locked(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_token_movement(
            self,
            context: DecoderContext,
            send_token_id: str,
            send_type: HistoryEventType,
            send_subtype: HistoryEventSubType,
            send_to_address: ChecksumEvmAddress,
            send_notes: str,
            receive_token_id: str,
            receive_type: HistoryEventType,
            receive_subtype: HistoryEventSubType,
            receive_notes: str,
    ) -> EvmDecodingOutput:
        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # Optimism GIV has 18 decimals
        )
        in_event, out_event = None, None
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.asset.identifier == send_token_id and
                    event.address == send_to_address and
                    amount == event.amount
            ):
                out_event = event
                event.event_type = send_type
                event.event_subtype = send_subtype
                event.counterparty = CPT_GIVETH
                event.notes = send_notes.format(amount=amount)
            elif (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.asset.identifier == receive_token_id and
                    event.location_label == user
            ):
                in_event = event
                event.event_type = receive_type
                event.event_subtype = receive_subtype
                event.counterparty = CPT_GIVETH
                event.notes = receive_notes.format(amount=event.amount)

        if in_event is None or out_event is None:
            log.error(f'Could not find the GIV/PoW token transfers for {context.transaction}')
            return DEFAULT_EVM_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return DEFAULT_EVM_DECODING_OUTPUT
