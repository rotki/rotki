from typing import Any

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.decoding.constants import CPT_HOP
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.frontend_structures.types import TransactionEventType
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.types import DECODER_EVENT_MAPPING, ChecksumEvmAddress
from rotkehlchen.utils.misc import from_wei, hex_or_bytes_to_address, hex_or_bytes_to_int

# https://github.com/hop-protocol/hop/blob/develop/packages/core/src/addresses/mainnet.ts
ETH_BRIDGE = string_to_evm_address('0xb8901acB165ed027E32754E0FFe830802919727f')

TRANSFER_TO_L2 = b'\n\x06\x07h\x8c\x86\xec\x17u\xab\xcd\xba\xb7\xb3::5\xa6\xc9\xcd\xe6w\xc9\xbe\x88\x01P\xc21\xcck\x0b'  # noqa: E501


# Probably this should go somewhere more central eventually
# and add other networks too. Added only hop supported ones now
chainid_to_name = {
    1: 'Ethereum Mainnet',
    10: 'Optimism',
    100: 'Gnosis Chain',
    137: 'Polygon',
    42161: 'Arbitrum One',
}


class HopDecoder(DecoderInterface):

    def _decode_send_eth(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != TRANSFER_TO_L2:
            return DEFAULT_DECODING_OUTPUT

        chain_id = hex_or_bytes_to_int(context.tx_log.topics[1])
        recipient = hex_or_bytes_to_address(context.tx_log.topics[2])
        amount_raw = hex_or_bytes_to_int(context.tx_log.data[:32])

        name = chainid_to_name.get(chain_id, f'Unknown Chain with id {chain_id}')
        amount = from_wei(FVal(amount_raw))

        for event in context.decoded_events:
            if event.event_type == HistoryEventType.SPEND and event.address == ETH_BRIDGE and event.asset == A_ETH and event.balance.amount == amount:  # noqa: E501
                if recipient == event.location_label:
                    target_str = 'at the same address'
                else:
                    target_str = f'at address {recipient}'
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_HOP
                event.notes = f'Bridge {amount} ETH to {name} {target_str} via Hop protocol'
                break

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def possible_events(self) -> DECODER_EVENT_MAPPING:
        return {CPT_HOP: {
            HistoryEventType.DEPOSIT: {
                HistoryEventSubType.BRIDGE: TransactionEventType.BRIDGE,
            },
        }}

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            ETH_BRIDGE: (self._decode_send_eth,),
        }

    def counterparties(self) -> list[str]:
        return [CPT_HOP]
