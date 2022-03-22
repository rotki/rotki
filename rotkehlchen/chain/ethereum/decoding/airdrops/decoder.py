from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from rotkehlchen.accounting.ledger_actions import LedgerActionType
from rotkehlchen.accounting.structures import (
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
    get_tx_event_type_identifier,
)
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import (
    ActionItem,
    TxEventSettings,
    TxMultitakeTreatment,
)
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_ethereum_address
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.constants.assets import A_1INCH, A_BADGER, A_UNI
from rotkehlchen.types import ChecksumEthAddress, EthereumTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot

UNISWAP_DISTRIBUTOR = string_to_ethereum_address('0x090D4613473dEE047c3f2706764f49E0821D256e')
UNISWAP_TOKEN_CLAIMED = b'N\xc9\x0e\x96U\x19\xd9&\x81&tg\xf7u\xad\xa5\xbd!J\xa9,\r\xc9=\x90\xa5\xe8\x80\xce\x9e\xd0&'  # noqa: E501

BADGERHUNT = string_to_ethereum_address('0x394DCfbCf25C5400fcC147EbD9970eD34A474543')
BADGER_HUNT_EVENT = b'\x8e\xaf\x15aI\x08\xa4\xe9\x02!A\xfeJYk\x1a\xb0\xcbr\xab2\xb2P#\xe3\xda*E\x9c\x9a3\\'  # noqa: E501

ONEINCH = string_to_ethereum_address('0xE295aD71242373C37C5FdA7B57F26f9eA1088AFe')
ONEINCH_CLAIMED = b'N\xc9\x0e\x96U\x19\xd9&\x81&tg\xf7u\xad\xa5\xbd!J\xa9,\r\xc9=\x90\xa5\xe8\x80\xce\x9e\xd0&'  # noqa: E501

CPT_UNISWAP = 'uniswap'
CPT_BADGER = 'badger'
CPT_ONEINCH = 'oneinch'


class AirdropsDecoder(DecoderInterface):  # lgtm[py/missing-call-to-init]

    def _decode_uniswap_claim(  # pylint: disable=no-self-use
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        if tx_log.topics[0] != UNISWAP_TOKEN_CLAIMED:
            return None, None

        user_address = hex_or_bytes_to_address(tx_log.data[32:64])
        raw_amount = hex_or_bytes_to_int(tx_log.data[64:96])
        amount = asset_normalized_value(amount=raw_amount, asset=A_UNI)

        for event in decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.location_label == user_address and amount == event.balance.amount and A_UNI == event.asset:  # noqa: E501
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.AIRDROP
                event.counterparty = CPT_UNISWAP
                event.notes = f'Claim {amount} UNI from uniswap airdrop'  # noqa: E501
                break

        return None, None

    def _decode_badger_claim(  # pylint: disable=no-self-use
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        if tx_log.topics[0] != BADGER_HUNT_EVENT:
            return None, None

        user_address = hex_or_bytes_to_address(tx_log.topics[1])
        raw_amount = hex_or_bytes_to_int(tx_log.data[32:64])
        amount = asset_normalized_value(amount=raw_amount, asset=A_BADGER)

        for event in decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.location_label == user_address and amount == event.balance.amount and A_BADGER == event.asset:  # noqa: E501
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.AIRDROP
                event.counterparty = CPT_BADGER
                event.notes = f'Claim {amount} BADGER from badger airdrop'  # noqa: E501
                break

        return None, None

    def _decode_oneinch_claim(  # pylint: disable=no-self-use
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        if tx_log.topics[0] != ONEINCH_CLAIMED:
            return None, None

        user_address = hex_or_bytes_to_address(tx_log.data[32:64])
        raw_amount = hex_or_bytes_to_int(tx_log.data[64:96])
        amount = asset_normalized_value(amount=raw_amount, asset=A_1INCH)

        for event in decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.location_label == user_address and amount == event.balance.amount and A_1INCH == event.asset:  # noqa: E501
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.AIRDROP
                event.counterparty = CPT_ONEINCH
                event.notes = f'Claim {amount} 1INCH from 1inch airdrop'  # noqa: E501
                break

        return None, None

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> Dict[ChecksumEthAddress, Tuple[Any, ...]]:
        return {
            UNISWAP_DISTRIBUTOR: (self._decode_uniswap_claim,),  # noqa: E501
            BADGERHUNT: (self._decode_badger_claim,),  # noqa: E501
            ONEINCH: (self._decode_oneinch_claim,),  # noqa: E501
        }

    def counterparties(self) -> List[str]:
        return [CPT_BADGER, CPT_UNISWAP, CPT_ONEINCH]

    def event_settings(self, pot: 'AccountingPot') -> Dict[str, 'TxEventSettings']:
        """Being defined at function call time is fine since this function is called only once"""
        airdrops_taxable = LedgerActionType.AIRDROP in pot.settings.taxable_ledger_actions
        return {
            get_tx_event_type_identifier(HistoryEventType.RECEIVE, HistoryEventSubType.AIRDROP, counterparty): TxEventSettings(  # noqa: E501
                count_pnl=airdrops_taxable,
                method='acquisition',
                take=1,
                multitake_treatment=None,
            )
            for counterparty in self.counterparties()
        }
