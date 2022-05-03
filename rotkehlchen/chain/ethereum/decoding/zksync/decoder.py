from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from rotkehlchen.accounting.structures.base import (
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
    get_tx_event_type_identifier,
)
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem, TxEventSettings
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_ethereum_address
from rotkehlchen.chain.ethereum.utils import asset_raw_value
from rotkehlchen.types import ChecksumEthAddress, EthereumTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot

DEPOSIT = b'\xb6\x86k\x02\x9f:\xa2\x9c\xd9\xe2\xbf\xf8\x15\x9a\x8c\xca\xa48\x9fz\x08|q\th\xe0\xb2\x00\xc0\xc7;\x08'  # noqa: E501

ZKSYNC_BRIDGE = string_to_ethereum_address('0xaBEA9132b05A70803a4E85094fD0e1800777fBEF')

CPT_ZKSYNC = 'zksync'


class ZksyncDecoder(DecoderInterface):  # lgtm[py/missing-call-to-init]

    def _decode_event(  # pylint: disable=no-self-use
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        if tx_log.topics[0] == DEPOSIT:
            return self._decode_deposit(tx_log, transaction, decoded_events, all_logs, action_items)  # noqa: E501

        return None, None

    def _decode_deposit(  # pylint: disable=no-self-use
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        """Match a zksync deposit with the transfer to decode it

        TODO: This is now quite bad. We don't use the token id of zksync as we should.
        Example: https://etherscan.io/tx/0xdd6d1f92980faf622c09acd84dbff4fe0bd7ae466a23c2479df709f8996d250e#eventlog
        We should include the zksync api querying module which is in this PR:
        https://github.com/rotki/rotki/pull/3985/files
        to get the ids of tokens and then match them to what is deposited.
        """  # noqa: E501
        user_address = hex_or_bytes_to_address(tx_log.topics[1])
        amount_raw = hex_or_bytes_to_int(tx_log.data)

        for event in decoded_events:
            if event.event_type == HistoryEventType.SPEND and event.location_label == user_address:
                event_raw_amount = asset_raw_value(amount=event.balance.amount, asset=event.asset)
                if event_raw_amount != amount_raw:
                    continue

                # found the deposit transfer
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_ZKSYNC
                event.notes = f'Deposit {event.balance.amount} {event.asset.symbol} to zksync'  # noqa: E501
                break

        return None, None

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> Dict[ChecksumEthAddress, Tuple[Any, ...]]:
        return {
            ZKSYNC_BRIDGE: (self._decode_event,),  # noqa: E501
        }

    def counterparties(self) -> List[str]:
        return [CPT_ZKSYNC]

    def event_settings(self, pot: 'AccountingPot') -> Dict[str, TxEventSettings]:  # pylint: disable=unused-argument  # noqa: E501
        """Being defined at function call time is fine since this function is called only once"""
        return {
            get_tx_event_type_identifier(HistoryEventType.DEPOSIT, HistoryEventSubType.BRIDGE, CPT_ZKSYNC): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='spend',
                take=1,
                multitake_treatment=None,
            ),
        }
