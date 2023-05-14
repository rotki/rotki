import logging
from typing import Any

from eth_utils import encode_hex
from rotkehlchen.accounting.structures.balance import Balance

from rotkehlchen.accounting.structures.eth2 import EthDepositEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.constants import ETH2_DEPOSIT_ADDRESS
from rotkehlchen.chain.ethereum.modules.curve.decoder import DEFAULT_DECODING_OUTPUT
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import DecoderContext, DecodingOutput
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails, EventCategory
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.beaconchain import BeaconChain
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, DecoderEventMappingType, Eth2PubKey
from rotkehlchen.utils.misc import from_gwei, hex_or_bytes_to_int

from .constants import CPT_ETH2, UNKNOWN_VALIDATOR_INDEX

DEPOSIT_EVENT = b'd\x9b\xbcb\xd0\xe3\x13B\xaf\xeaN\\\xd8-@I\xe7\xe1\xee\x91/\xc0\x88\x9a\xa7\x90\x80;\xe3\x908\xc5'  # noqa: E501

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Eth2Decoder(DecoderInterface):

    def _decode_eth2_deposit_event(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != DEPOSIT_EVENT:
            return DEFAULT_DECODING_OUTPUT

        public_key = Eth2PubKey(encode_hex(context.tx_log.data[192:240]))
        amount = from_gwei(hex_or_bytes_to_int(context.tx_log.data[352:360], byteorder='little'))

        validator_index = UNKNOWN_VALIDATOR_INDEX
        extra_data = None
        with self.base.database.conn.read_ctx() as cursor:
            result = cursor.execute(
                'SELECT validator_index FROM eth2_validators WHERE public_key=?',
                (public_key,),
            ).fetchone()
            if result is not None:
                validator_index = result[0]
            else:  # We ask beaconchain. Instead of pushing it to decoders, recreating here
                # this is not good practise since if it shares any backoff logic it breaks,
                # but yoloing it since it's a single query that won't happen often
                # and the alternative of pushing beaconchain as an argument across all
                # decoders seems wrong, dirty and breaking abstraction
                try:
                    beaconchain = BeaconChain(self.base.database, self.msg_aggregator)
                except RemoteError as e:
                    log.error(f'Failed to query validator index for {public_key} due to {e!s}')
                    extra_data = {'public_key': public_key}
                else:
                    result = beaconchain.get_validator_data([public_key])
                    validator_index = result[0]['validatorindex']
                    if not isinstance(validator_index, int) or validator_index < 0:
                        validator_index = UNKNOWN_VALIDATOR_INDEX
                        extra_data = {'public_key': public_key}

        for idx, event in enumerate(context.decoded_events):
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_ETH and
                event.balance.amount >= amount
            ):
                assert event.location_label is not None
                eth_deposit_event = EthDepositEvent(
                    tx_hash=context.transaction.tx_hash,
                    validator_index=validator_index,
                    sequence_index=self.base.get_next_sequence_counter(),
                    timestamp=event.timestamp,
                    balance=Balance(amount=amount),
                    depositor=string_to_evm_address(event.location_label),
                    extra_data=extra_data,  # only used if validator index is unknown
                )
                if event.balance.amount == amount:  # If amount is the same, replace the event
                    context.decoded_events[idx] = eth_deposit_event
                    return DEFAULT_DECODING_OUTPUT
                else:  # If amount is less, subtract the amount from the event and return new event
                    event.balance.amount -= amount
                    return DecodingOutput(event=eth_deposit_event)

        log.error(
            f'While decoding ETH deposit event {context.transaction.tx_hash.hex()} for public key '
            f'{public_key} could not find the send event',
        )
        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def possible_events(self) -> DecoderEventMappingType:
        return {CPT_ETH2: {
            HistoryEventType.STAKING: {
                HistoryEventSubType.DEPOSIT_ASSET: EventCategory.DEPOSIT,
            },
        }}

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            ETH2_DEPOSIT_ADDRESS: (self._decode_eth2_deposit_event,),
        }

    def counterparties(self) -> list[CounterpartyDetails]:
        return [CounterpartyDetails(identifier=CPT_ETH2, label='ETH2', image='ethereum.svg')]
