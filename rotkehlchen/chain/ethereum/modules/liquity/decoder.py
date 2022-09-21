from typing import Any, Dict, List, Optional, Tuple

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_LUSD
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction

from .constants import CPT_LIQUITY

BALANCE_UPDATE = b'\xca#+Z\xbb\x98\x8cT\x0b\x95\x9f\xf6\xc3\xbf\xae>\x97\xff\xf9d\xfd\t\x8cP\x8f\x96\x13\xc0\xa6\xbf\x1a\x80'  # noqa: E501
STABILITY_POOL = string_to_evm_address('0xDf9Eb223bAFBE5c5271415C75aeCD68C21fE3D7F')


class LiquityDecoder(DecoderInterface):  # lgtm[py/missing-call-to-init]

    @staticmethod
    def _decode_trove_operations(
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        if tx_log.topics[0] != BALANCE_UPDATE:
            return None, None
        resolved_lusd = A_LUSD.resolve_to_crypto_asset()

        for event in decoded_events:
            crypto_asset = event.asset.resolve_to_crypto_asset()
            if event.event_type == HistoryEventType.RECEIVE and event.asset == A_LUSD:
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.GENERATE_DEBT
                event.counterparty = CPT_LIQUITY
                event.notes = f'Generate {event.balance.amount} {resolved_lusd.symbol} from liquity'  # noqa: E501
            elif event.event_type == HistoryEventType.SPEND and event.asset == A_LUSD:
                event.event_type = HistoryEventType.SPEND
                event.event_subtype = HistoryEventSubType.PAYBACK_DEBT
                event.counterparty = CPT_LIQUITY
                event.notes = f'Return {event.balance.amount} {resolved_lusd.symbol} to liquity'
            elif event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE and event.asset == A_ETH:  # noqa: E501
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_LIQUITY
                event.notes = f'Deposit {event.balance.amount} {crypto_asset.symbol} as collateral for liquity'  # noqa: E501
            elif event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.asset == A_ETH:  # noqa: E501
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_LIQUITY
                event.notes = f'Withdraw {event.balance.amount} {crypto_asset.symbol} collateral from liquity'  # noqa: E501
        return None, None

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> Dict[ChecksumEvmAddress, Tuple[Any, ...]]:
        return {
            STABILITY_POOL: (self._decode_trove_operations,),  # noqa: E501
        }

    def counterparties(self) -> List[str]:
        return [CPT_LIQUITY]
