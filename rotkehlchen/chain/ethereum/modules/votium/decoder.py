from typing import Any, Dict, List, Optional, Tuple

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, ethaddress_to_asset
from rotkehlchen.types import ChecksumEvmAddress, EthereumTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import CPT_VOTIUM

VOTIUM_CLAIM = b'Gf\x92\x1f\\Ydm"\xd7\xd2f\xa2\x91d\xc8\xe9b6\x84\xd8\xdf\xdb\xd91s\x1d\xfd\xca\x02R8'  # noqa: E501
VOTIUM_CONTRACT = string_to_evm_address('0x378Ba9B73309bE80BF4C2c027aAD799766a7ED5A')


class VotiumDecoder(DecoderInterface):  # lgtm[py/missing-call-to-init]

    def _decode_claim(  # pylint: disable=no-self-use
        self,
        tx_log: EthereumTxReceiptLog,
        transaction: EthereumTransaction,  # pylint: disable=unused-argument
        decoded_events: List[HistoryBaseEntry],
        all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
        action_items: Optional[List[ActionItem]],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        if tx_log.topics[0] != VOTIUM_CLAIM:
            return None, None

        claimed_token_address = hex_or_bytes_to_address(tx_log.topics[1])
        claimed_token = ethaddress_to_asset(claimed_token_address)
        if claimed_token is None:
            return None, None

        receiver = hex_or_bytes_to_address(tx_log.topics[2])
        claimed_amount_raw = hex_or_bytes_to_int(tx_log.data[32:64])
        amount = asset_normalized_value(amount=claimed_amount_raw, asset=claimed_token)

        for event in decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.location_label == receiver and event.balance.amount == amount and claimed_token == event.asset:  # noqa: E501
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_VOTIUM
                event.notes = f'Receive {event.balance.amount} {event.asset.symbol} from votium bribe'  # noqa: E501

        return None, None

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> Dict[ChecksumEvmAddress, Tuple[Any, ...]]:
        return {
            VOTIUM_CONTRACT: (self._decode_claim,),
        }

    def counterparties(self) -> List[str]:
        return [CPT_VOTIUM]
