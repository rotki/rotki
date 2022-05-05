from typing import Any, Dict, List, Literal, Optional, Tuple

from rotkehlchen.accounting.structures.base import (
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_ethereum_address
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.constants.assets import A_1INCH, A_BADGER, A_CVX, A_FPIS, A_UNI
from rotkehlchen.types import ChecksumEthAddress, EthereumTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import AIRDROPS_LIST, CPT_BADGER, CPT_CONVEX, CPT_FRAX, CPT_ONEINCH, CPT_UNISWAP

UNISWAP_DISTRIBUTOR = string_to_ethereum_address('0x090D4613473dEE047c3f2706764f49E0821D256e')
UNISWAP_TOKEN_CLAIMED = b'N\xc9\x0e\x96U\x19\xd9&\x81&tg\xf7u\xad\xa5\xbd!J\xa9,\r\xc9=\x90\xa5\xe8\x80\xce\x9e\xd0&'  # noqa: E501

BADGERHUNT = string_to_ethereum_address('0x394DCfbCf25C5400fcC147EbD9970eD34A474543')
BADGER_HUNT_EVENT = b'\x8e\xaf\x15aI\x08\xa4\xe9\x02!A\xfeJYk\x1a\xb0\xcbr\xab2\xb2P#\xe3\xda*E\x9c\x9a3\\'  # noqa: E501

ONEINCH = string_to_ethereum_address('0xE295aD71242373C37C5FdA7B57F26f9eA1088AFe')
ONEINCH_CLAIMED = b'N\xc9\x0e\x96U\x19\xd9&\x81&tg\xf7u\xad\xa5\xbd!J\xa9,\r\xc9=\x90\xa5\xe8\x80\xce\x9e\xd0&'  # noqa: E501

FPIS = string_to_ethereum_address('0x61A1f84F12Ba9a56C22c31dDB10EC2e2CA0ceBCf')
CONVEX = string_to_ethereum_address('0x2E088A0A19dda628B4304301d1EA70b114e4AcCd')
FPIS_CONVEX_CLAIM = b'G\xce\xe9|\xb7\xac\xd7\x17\xb3\xc0\xaa\x145\xd0\x04\xcd[<\x8cW\xd7\r\xbc\xebNDX\xbb\xd6\x0e9\xd4'  # noqa: E501


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

    def _decode_fpis_claim(  # pylint: disable=no-self-use
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: List[ActionItem],  # pylint: disable=unused-argument
            airdrop: Literal['convex', 'fpis'],
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        if tx_log.topics[0] != FPIS_CONVEX_CLAIM:
            return None, None

        user_address = hex_or_bytes_to_address(tx_log.data[0:32])
        raw_amount = hex_or_bytes_to_int(tx_log.data[32:64])
        if airdrop == CPT_CONVEX:
            amount = asset_normalized_value(amount=raw_amount, asset=A_CVX)
            note_location = 'from convex airdrop'
            counterparty = CPT_CONVEX
        else:
            amount = asset_normalized_value(amount=raw_amount, asset=A_FPIS)
            note_location = 'from FPIS airdrop'
            counterparty = CPT_FRAX

        for event in decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.location_label == user_address and amount == event.balance.amount and A_FPIS == event.asset:  # noqa: E501
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.AIRDROP
                event.counterparty = counterparty
                event.notes = f'Claim {amount} {event.asset.symbol} {note_location}'  # noqa: E501
                break

        return None, None

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> Dict[ChecksumEthAddress, Tuple[Any, ...]]:
        return {
            UNISWAP_DISTRIBUTOR: (self._decode_uniswap_claim,),
            BADGERHUNT: (self._decode_badger_claim,),
            ONEINCH: (self._decode_oneinch_claim,),
            FPIS: (self._decode_fpis_claim, 'fpis'),
            CONVEX: (self._decode_fpis_claim, 'convex'),
        }

    def counterparties(self) -> List[str]:
        return AIRDROPS_LIST
