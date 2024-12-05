import logging
from typing import Any, Final

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.optimism.modules.giveth.constants import (
    CPT_GIVETH,
    GIV_DISTRO,
    GIV_TOKEN_ID,
    GIVPOW_TOKEN_ID,
    GIVPOWER_STAKING,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

TOKEN_DEPOSITED: Final = b'+\xc1}\xef\xafP\xe9\x01\x0bWhY\xc1GB\x1d\n\xafqT^\xe0\xbd\xf6\\J\xea\xfcm\xee\x9c/'  # noqa: E501
TOKEN_LOCKED: Final = b'yG{\x88\xdey~\x163\xf0\xb8\xb1\xd9p\xd4\xdfu\xbdK%\x84y}\xef\x16\x1f)\xabf}:w'  # noqa: E501
DEPOSIT_TOKEN_WITHDRAWN = b'=\x81U\xb4\xc5du\xf1\xae\x1bn\xb3\x11n;\xe1.3V\xca\x00\xa5\x9f\xe0+\x0f\x8c\x80\xe9\x01\xd2\xa7'  # noqa: E501
CLAIM: Final = b'G\xce\xe9|\xb7\xac\xd7\x17\xb3\xc0\xaa\x145\xd0\x04\xcd[<\x8cW\xd7\r\xbc\xebNDX\xbb\xd6\x0e9\xd4'  # noqa: E501


class GivethDecoder(DecoderInterface):

    def decode_staking_events(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == TOKEN_DEPOSITED:
            return self._decode_token_movement(
                context=context,
                send_token_id=GIV_TOKEN_ID,
                send_type=HistoryEventType.DEPOSIT,
                send_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                send_to_address=context.tx_log.address,
                send_notes='Deposit {amount} GIV for staking',
                receive_token_id=GIVPOW_TOKEN_ID,
                receive_type=HistoryEventType.RECEIVE,
                receive_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                receive_notes='Receive {amount} POW after depositing GIV',
            )
        elif context.tx_log.topics[0] == DEPOSIT_TOKEN_WITHDRAWN:
            return self._decode_token_movement(
                context=context,
                send_token_id=GIVPOW_TOKEN_ID,
                send_type=HistoryEventType.SPEND,
                send_subtype=HistoryEventSubType.RETURN_WRAPPED,
                send_to_address=ZERO_ADDRESS,
                send_notes='Return {amount} POW to Giveth staking',
                receive_token_id=GIV_TOKEN_ID,
                receive_type=HistoryEventType.WITHDRAWAL,
                receive_subtype=HistoryEventSubType.REMOVE_ASSET,
                receive_notes='Withdraw {amount} GIV from staking',
            )
        elif context.tx_log.topics[0] == TOKEN_LOCKED:
            return self._decode_token_locked(context)

        return DEFAULT_DECODING_OUTPUT

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
    ) -> DecodingOutput:
        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_DECODING_OUTPUT

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
                    amount == event.balance.amount
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
                event.notes = receive_notes.format(amount=event.balance.amount)

        if in_event is None or out_event is None:
            log.error(f'Could not find the GIV/PoW token transfers for {context.transaction}')
            return DEFAULT_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return DEFAULT_DECODING_OUTPUT

    def _decode_token_locked(self, context: DecoderContext) -> DecodingOutput:
        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # Optimism GIV has 18 decimals
        )
        rounds = int.from_bytes(context.tx_log.data[32:64])

        lock_event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset(GIV_TOKEN_ID),
            balance=Balance(amount),
            location_label=user,
            notes=f'Lock {amount} GIV for {rounds} round/s',
            address=context.tx_log.address,
            counterparty=CPT_GIVETH,
        )
        receive_event = None
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.asset.identifier == GIVPOW_TOKEN_ID and
                    event.location_label == user
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = CPT_GIVETH
                event.notes = f'Receive {event.balance.amount} POW after locking GIV'
                receive_event = event
                break

        else:
            log.error(f'Could not find the GivPoW token transfer after locking GIV for {context.transaction}')  # noqa: E501

        maybe_reshuffle_events(
            ordered_events=[lock_event, receive_event],
            events_list=context.decoded_events,
        )
        return DecodingOutput(event=lock_event)

    def decode_claim(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != CLAIM:
            return DEFAULT_DECODING_OUTPUT

        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # Optimism GIV has 18 decimals
        )
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.asset.identifier == GIV_TOKEN_ID and
                    event.location_label == user and
                    amount == event.balance.amount
            ):
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_GIVETH
                event.notes = f'Claim {amount} GIV as staking reward'
                break
        else:
            log.error(f'Could not find the Giv token transfer after reward claiming for {context.transaction}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            GIVPOWER_STAKING: (self.decode_staking_events,),
            GIV_DISTRO: (self.decode_claim,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_GIVETH,
            label='Giveth',
            image='giveth.jpg',
),)
