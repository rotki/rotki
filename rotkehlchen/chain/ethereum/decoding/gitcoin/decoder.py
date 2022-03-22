import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from rotkehlchen.accounting.structures import (
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
    get_tx_event_type_identifier,
)
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem, TxEventSettings
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_ethereum_address
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, ethaddress_to_asset
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEthAddress, EthereumTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.chain.ethereum.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


GITCOIN_BULK_CHECKOUT = string_to_ethereum_address('0x7d655c57f71464B6f83811C55D84009Cd9f5221C')

DONATION_SENT = b';\xb7B\x8b%\xf9\xbd\xad\x9b\xd2\xfa\xa4\xc6\xa7\xa9\xe5\xd5\x88&W\xe9l\x1d$\xccA\xc1\xd6\xc1\x91\n\x98'  # noqa: E501

CPT_GITCOIN = 'gitcoin'


class GitcoinDecoder(DecoderInterface):  # lgtm[py/missing-call-to-init]
    def __init__(  # pylint: disable=super-init-not-called
            self,
            ethereum_manager: 'EthereumManager',  # pylint: disable=unused-argument
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',  # pylint: disable=unused-argument
    ) -> None:
        self.base = base_tools

    def _decode_donation_sent(
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: Optional[List[ActionItem]],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        if tx_log.topics[0] != DONATION_SENT:
            return None, None

        donor = hex_or_bytes_to_address(tx_log.topics[3])
        if not self.base.is_tracked(donor):
            return None, None

        token_address = hex_or_bytes_to_address(tx_log.topics[1])
        token = ethaddress_to_asset(token_address)
        if token is None:
            log.debug(f'Could not decode token {token_address} for gitcoin donation')
            return None, None
        raw_amount = hex_or_bytes_to_int(tx_log.topics[2])
        amount = asset_normalized_value(raw_amount, token)
        dst_address = hex_or_bytes_to_address(tx_log.data)

        # Transfer event should follow, so create action item
        action_item = ActionItem(
            action='transform',
            sequence_index=tx_log.log_index,
            from_event_type=HistoryEventType.SPEND,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=token,
            amount=amount,
            to_event_subtype=HistoryEventSubType.DONATE,
            to_notes=f'Donate {amount} {token.symbol} to gitcoin grant {dst_address}',
            to_counterparty=CPT_GITCOIN,
        )
        return None, action_item

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> Dict[ChecksumEthAddress, Tuple[Any, ...]]:
        return {
            GITCOIN_BULK_CHECKOUT: (self._decode_donation_sent,),  # noqa: E501
        }

    def counterparties(self) -> List[str]:
        return [CPT_GITCOIN]

    def event_settings(self, pot: 'AccountingPot') -> Dict[str, TxEventSettings]:  # pylint: disable=unused-argument  # noqa: E501
        """Being defined at function call time is fine since this function is called only once"""
        return {
            get_tx_event_type_identifier(HistoryEventType.SPEND, HistoryEventSubType.DONATE, CPT_GITCOIN): TxEventSettings(  # noqa: E501
                count_pnl=True,
                method='spend',
                take=1,
                multitake_treatment=None,
            ),
        }
