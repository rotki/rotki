from typing import Any

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.utils import asset_raw_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails, EventCategory
from rotkehlchen.types import ChecksumEvmAddress, DecoderEventMappingType
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import CPT_ZKSYNC, ZKSYNC_BRIDGE

ONCHAIN_DEPOSIT = b'\xb6\x86k\x02\x9f:\xa2\x9c\xd9\xe2\xbf\xf8\x15\x9a\x8c\xca\xa48\x9fz\x08|q\th\xe0\xb2\x00\xc0\xc7;\x08'  # noqa: E501
DEPOSIT = b'\x8f_QD\x83\x94i\x9a\xd6\xa3\xb8\x0c\xda\xdfN\xc6\x8c]rL\x8c?\xea\t\xbe\xa5[<-\x0e-\xd0'  # noqa: E501
NEW_PRIORITY_REQUEST = b'\xd0\x943r\xc0\x8bC\x8a\x88\xd4\xb3\x9dw!i\x01\x07\x9e\xda\x9c\xa5\x9dE4\x98A\xc0\x99\x08;h0'  # noqa: E501


class ZksyncDecoder(DecoderInterface):

    def _decode_event(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == ONCHAIN_DEPOSIT:
            user_address = hex_or_bytes_to_address(context.tx_log.topics[1])
            return self._decode_deposit(context, user_address)
        elif context.tx_log.topics[0] == DEPOSIT:
            for tx_log in context.all_logs:  # iterate
                if tx_log.topics[0] == NEW_PRIORITY_REQUEST:
                    op_type = hex_or_bytes_to_int(tx_log.data[64:96])
                    if op_type != 1:
                        continue  # 1 is deposit and this is what we are searching for
                    user_address = hex_or_bytes_to_address(tx_log.data[0:32])
                    return self._decode_deposit(context, user_address)

        return DEFAULT_DECODING_OUTPUT

    def _decode_deposit(self, context: DecoderContext, user_address: ChecksumEvmAddress) -> DecodingOutput:  # noqa: E501
        """Match a zksync deposit with the transfer to decode it

        TODO: This is now quite bad. We don't use the token id of zksync as we should.
        Example: https://etherscan.io/tx/0xdd6d1f92980faf622c09acd84dbff4fe0bd7ae466a23c2479df709f8996d250e#eventlog
        We should include the zksync api querying module which is in this PR:
        https://github.com/rotki/rotki/pull/3985/files
        to get the ids of tokens and then match them to what is deposited.
        """
        amount_raw = hex_or_bytes_to_int(context.tx_log.data)

        for event in context.decoded_events:
            if event.event_type == HistoryEventType.SPEND and event.location_label == user_address:
                resolved_event_asset = event.asset.resolve_to_crypto_asset()
                event_raw_amount = asset_raw_value(
                    amount=event.balance.amount,
                    asset=resolved_event_asset,
                )
                if event_raw_amount != amount_raw:
                    continue

                # found the deposit transfer
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_ZKSYNC
                crypto_asset = resolved_event_asset
                event.notes = f'Deposit {event.balance.amount} {crypto_asset.symbol} to zksync'  # noqa: E501
                break

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def possible_events(self) -> DecoderEventMappingType:
        return {
            CPT_ZKSYNC: {
                HistoryEventType.DEPOSIT: {
                    HistoryEventSubType.BRIDGE: EventCategory.BRIDGE_IN,
                },
            },
        }

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            ZKSYNC_BRIDGE: (self._decode_event,),
        }

    def counterparties(self) -> list[CounterpartyDetails]:
        return [CounterpartyDetails(identifier=CPT_ZKSYNC, label='zkSync', image='zksync.jpg')]
