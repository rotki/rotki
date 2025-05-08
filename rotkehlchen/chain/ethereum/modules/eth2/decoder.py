import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.constants import ETH2_DEPOSIT_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.eth2 import EthDepositEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Eth2PubKey
from rotkehlchen.utils.misc import bytes_to_address, bytes_to_hexstr, from_gwei

from .constants import CONSOLIDATION_REQUEST_CONTRACT, CPT_ETH2, UNKNOWN_VALIDATOR_INDEX

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.externalapis.beaconchain.service import BeaconChain
    from rotkehlchen.user_messages import MessagesAggregator

DEPOSIT_EVENT = b'd\x9b\xbcb\xd0\xe3\x13B\xaf\xeaN\\\xd8-@I\xe7\xe1\xee\x91/\xc0\x88\x9a\xa7\x90\x80;\xe3\x908\xc5'  # noqa: E501

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Eth2Decoder(DecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            beacon_chain: 'BeaconChain',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.beacon_chain = beacon_chain

    def _query_validator_indexes(self, public_keys: list[Eth2PubKey]) -> list[int]:
        """Retrieve the validator indexes of the specified public keys
        from either the db or beaconchain.
        """
        with self.base.database.conn.read_ctx() as cursor:
            found_indexes = dict(cursor.execute(
                'SELECT public_key, validator_index FROM eth2_validators '
                f"WHERE public_key IN ({','.join(['?'] * len(public_keys))})",
                public_keys,
            ))

        unknown_keys = [key for key in public_keys if key not in found_indexes]
        if len(unknown_keys) != 0:  # Query beaconchain.
            try:
                for result in self.beacon_chain.get_validator_data(unknown_keys):
                    validator_index = result['validatorindex']
                    if isinstance(validator_index, int) and validator_index >= 0:
                        found_indexes[result['pubkey']] = validator_index
            except RemoteError as e:
                log.error(f'Failed to query validator index for {unknown_keys} due to {e!s}')

        return [found_indexes.get(key, UNKNOWN_VALIDATOR_INDEX) for key in public_keys]

    def _get_indexes_or_public_keys(self, public_keys: list[Eth2PubKey]) -> list[int | Eth2PubKey]:
        """Query the validator indexes but fall back to the public key if the index is unknown."""
        return [
            validator_index if validator_index != UNKNOWN_VALIDATOR_INDEX else public_key
            for validator_index, public_key in zip(
                self._query_validator_indexes(public_keys=public_keys),
                public_keys,
                strict=False,  # the list from _query_validator_indexes will be the same length as the original list  # noqa: E501
            )
        ]

    def _decode_eth2_deposit_event(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != DEPOSIT_EVENT:
            return DEFAULT_DECODING_OUTPUT

        public_key = Eth2PubKey(bytes_to_hexstr(context.tx_log.data[192:240]))
        amount = from_gwei(int.from_bytes(context.tx_log.data[352:360], byteorder='little'))
        validator_index = self._query_validator_indexes(public_keys=[public_key])[0]
        extra_data = {'public_key': public_key} if validator_index == UNKNOWN_VALIDATOR_INDEX else None  # noqa: E501
        for idx, event in enumerate(context.decoded_events):
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_ETH and
                event.amount >= amount
            ):
                assert event.location_label is not None
                eth_deposit_event = EthDepositEvent(
                    tx_hash=context.transaction.tx_hash,
                    validator_index=validator_index,
                    sequence_index=self.base.get_next_sequence_index(),
                    timestamp=event.timestamp,
                    amount=amount,
                    depositor=string_to_evm_address(event.location_label),
                    extra_data=extra_data,  # only used if validator index is unknown
                )
                if event.amount == amount:  # If amount is the same, replace the event
                    context.decoded_events[idx] = eth_deposit_event
                    return DEFAULT_DECODING_OUTPUT
                else:  # If amount is less, subtract the amount from the event and return new event
                    event.amount -= amount
                    return DecodingOutput(event=eth_deposit_event)

        log.error(
            f'While decoding ETH deposit event {context.transaction.tx_hash.hex()} for public key '
            f'{public_key} could not find the send event',
        )
        return DEFAULT_DECODING_OUTPUT

    def _decode_eth2_consolidation_request(self, context: DecoderContext) -> DecodingOutput:
        """Decode a request to consolidate validators.
        Handles two types of requests:
        - Self consolidation - changes the withdrawal credentials to 0x02 (accumulating validator)
          See https://epf.wiki/?ref=blog.obol.org#/wiki/pectra-faq?id=q-i-have-a-validator-with-0x01-credentials-how-do-i-move-to-0x02
        - Normal consolidation - consolidates the source validator into the target validator
        """
        if len(context.tx_log.data) != 116:  # This an anonymous tx log so can't check topic[0]
            log.warning(
                f'Encountered ETH2 consolidation request with unexpected '
                f'data length in transaction {context.transaction}',
            )
            return DEFAULT_DECODING_OUTPUT

        for event in context.decoded_events:
            if (
                event.address == CONSOLIDATION_REQUEST_CONTRACT and
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_ETH
            ):
                event.event_subtype = HistoryEventSubType.FEE
                event.counterparty = CPT_ETH2
                event.notes = f'Spend {event.amount} ETH as validator consolidation fee'

        caller_address = bytes_to_address(b'\x00' * 12 + context.tx_log.data[:20])
        source_public_key = Eth2PubKey(bytes_to_hexstr(context.tx_log.data[20:68]))
        target_public_key = Eth2PubKey(bytes_to_hexstr(context.tx_log.data[68:116]))
        if source_public_key == target_public_key:
            target = self._get_indexes_or_public_keys(public_keys=[target_public_key])[0]
            notes = f'Request to convert validator {target} into an accumulating validator'
        else:
            source, target = self._get_indexes_or_public_keys(
                public_keys=[source_public_key, target_public_key],
            )
            notes = f'Request to consolidate validator {source} into {target}'

        return DecodingOutput(event=self.base.make_event_next_index(
            tx_hash=context.transaction.tx_hash,
            timestamp=context.transaction.timestamp,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=caller_address,
            notes=notes,
            address=context.tx_log.address,
            counterparty=CPT_ETH2,
        ))

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            ETH2_DEPOSIT_ADDRESS: (self._decode_eth2_deposit_event,),
            CONSOLIDATION_REQUEST_CONTRACT: (self._decode_eth2_consolidation_request,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_ETH2, label='ETH2', image='ethereum.svg'),)
