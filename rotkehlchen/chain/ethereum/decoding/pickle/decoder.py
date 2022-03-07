from typing import Any, Dict, List, Optional, Tuple

from rotkehlchen.accounting.structures import (
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_ethereum_address
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, ethaddress_to_asset
from rotkehlchen.types import ChecksumEthAddress, EthereumTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

P_LOOKS = string_to_ethereum_address('0xb4EBc2C371182DeEa04B2264B9ff5AC4F0159C69')


class PickleDecoder(DecoderInterface):  # lgtm[py/missing-call-to-init]

    def _decode_deposit(  # pylint: disable=no-self-use
        self,
        tx_log: EthereumTxReceiptLog,
        transaction: EthereumTransaction,
        decoded_events: List[HistoryBaseEntry],
        all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
        action_items: Optional[List[ActionItem]],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        if tx_log.topics[0] != ERC20_OR_ERC721_TRANSFER:
            return None, None

        contract_address = transaction.to_address

        sender = hex_or_bytes_to_address(tx_log.topics[1])
        receiver = hex_or_bytes_to_address(tx_log.topics[2])
        amount_raw = hex_or_bytes_to_int(tx_log.data)

        for event in decoded_events:
            #import pdb; pdb.set_trace()
            if event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE and event.location_label == transaction.from_address:
                sent_token = event.asset
                amount = asset_normalized_value(amount=amount_raw, asset=sent_token)
                #import pdb; pdb.set_trace()
                if event.balance.amount == amount:  # noqa: E501
                    event.event_type = HistoryEventType.STAKING
                    event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    event.counterparty = 'pickle finance'
                    event.notes = f'Deposit {event.balance.amount} {event.asset.symbol} in pickle contract'  # noqa: E501
            if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.location_label == transaction.from_address:
                sent_token = event.asset
                amount = asset_normalized_value(amount=amount_raw, asset=sent_token)
                #import pdb; pdb.set_trace()
                if event.balance.amount == amount:  # noqa: E501
                    event.event_type = HistoryEventType.STAKING
                    event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    event.counterparty = 'pickle finance'
                    event.notes = f'Deposit {event.balance.amount} {event.asset.symbol} in pickle contract'  # noqa: E501

            
        return None, None

    def addresses_to_decoders(self) -> Dict[ChecksumEthAddress, Tuple[Any, ...]]:
        return {
            P_LOOKS: (self._decode_deposit,),
        }
