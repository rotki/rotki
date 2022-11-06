from typing import Any, Dict, List, Optional, Tuple

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import from_wei, hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import CPT_HOP

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


class HopDecoder(DecoderInterface):  # lgtm[py/missing-call-to-init]

    def _decode_send_eth(  # pylint: disable=no-self-use
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], List[ActionItem]]:
        if tx_log.topics[0] != TRANSFER_TO_L2:
            return None, []

        chain_id = hex_or_bytes_to_int(tx_log.topics[1])
        recipient = hex_or_bytes_to_address(tx_log.topics[2])
        amount_raw = hex_or_bytes_to_int(tx_log.data[:32])

        name = chainid_to_name.get(chain_id, f'Unknown Chain with id {chain_id}')
        amount = from_wei(FVal(amount_raw))

        for event in decoded_events:
            if event.event_type == HistoryEventType.SPEND and event.counterparty == ETH_BRIDGE and event.asset == A_ETH and event.balance.amount == amount:  # noqa: E501
                if recipient == event.location_label:
                    target_str = 'at the same address'
                else:
                    target_str = f'at address {recipient}'
                event.event_type = HistoryEventType.TRANSFER
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_HOP
                event.notes = f'Bridge {amount} ETH to {name} {target_str} via Hop protocol'
                break

        return None, []

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> Dict[ChecksumEvmAddress, Tuple[Any, ...]]:
        return {
            ETH_BRIDGE: (self._decode_send_eth,),
        }

    def counterparties(self) -> List[str]:
        return [CPT_HOP]
