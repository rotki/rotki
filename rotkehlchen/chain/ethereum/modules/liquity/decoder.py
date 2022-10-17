import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.constants.assets import A_ETH, A_LQTY, A_LUSD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_int

from .constants import CPT_LIQUITY

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.user_messages import MessagesAggregator

BALANCE_UPDATE = b'\xca#+Z\xbb\x98\x8cT\x0b\x95\x9f\xf6\xc3\xbf\xae>\x97\xff\xf9d\xfd\t\x8cP\x8f\x96\x13\xc0\xa6\xbf\x1a\x80'  # noqa: E501
ACTIVE_POOL = string_to_evm_address('0xDf9Eb223bAFBE5c5271415C75aeCD68C21fE3D7F')
STABILITY_POOL = string_to_evm_address('0x66017D22b0f8556afDd19FC67041899Eb65a21bb')

STABILITY_POOL_GAIN_WITHDRAW = b'QEr"\xeb\xca\x92\xc35\xc9\xc8n+\xaa\x1c\xc0\xe4\x0f\xfa\xa9\x08JQE)\x80\xd5\xba\x8d\xec/c'  # noqa: E501
STABILITY_POOL_LQTY_PAID = b'&\x08\xb9\x86\xa6\xac\x0flb\x9c\xa3p\x18\xe8\n\xf5V\x1e6bR\xae\x93`*\x96\xd3\xab.s\xe4-'  # noqa: E501
STABILITY_POOL_EVENTS = {STABILITY_POOL_GAIN_WITHDRAW, STABILITY_POOL_LQTY_PAID}

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class LiquityDecoder(DecoderInterface):  # lgtm[py/missing-call-to-init]

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            ethereum_manager=ethereum_manager,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.lusd = A_LUSD.resolve_to_crypto_asset()
        self.eth = A_ETH.resolve_to_crypto_asset()
        self.lqty = A_LQTY.resolve_to_evm_token()

    def _decode_trove_operations(
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], List[ActionItem]]:
        if tx_log.topics[0] != BALANCE_UPDATE:
            return None, []

        for event in decoded_events:
            try:
                crypto_asset = event.asset.resolve_to_crypto_asset()
            except (UnknownAsset, WrongAssetType):
                self.notify_user(event=event, counterparty=CPT_LIQUITY)
                continue
            if event.event_type == HistoryEventType.RECEIVE and event.asset == A_LUSD:
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.GENERATE_DEBT
                event.counterparty = CPT_LIQUITY
                event.notes = f'Generate {event.balance.amount} {self.lusd.symbol} from liquity'  # noqa: E501
            elif event.event_type == HistoryEventType.SPEND and event.asset == A_LUSD:
                event.event_type = HistoryEventType.SPEND
                event.event_subtype = HistoryEventSubType.PAYBACK_DEBT
                event.counterparty = CPT_LIQUITY
                event.notes = f'Return {event.balance.amount} {self.lusd.symbol} to liquity'
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
        return None, []

    def _decode_stability_pool_event(
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], List[ActionItem]]:
        if tx_log.topics[0] not in STABILITY_POOL_EVENTS:
            return None, []

        collected_eth, collected_lqty = ZERO, ZERO
        if tx_log.topics[0] == STABILITY_POOL_GAIN_WITHDRAW:
            collected_eth = asset_normalized_value(
                amount=hex_or_bytes_to_int(tx_log.data[0:32]),
                asset=self.eth,
            )
        elif tx_log.topics[0] == STABILITY_POOL_LQTY_PAID:
            collected_lqty = asset_normalized_value(
                amount=hex_or_bytes_to_int(tx_log.data[0:32]),
                asset=self.lqty,
            )

        for event in decoded_events:
            if event.event_type == HistoryEventType.SPEND and event.asset == A_LUSD:
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_LIQUITY
                event.notes = f"Deposit {event.balance.amount} {self.lusd.symbol} in liquity's stability pool"  # noqa: E501
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                (
                    event.asset == self.eth and
                    event.balance.amount == collected_eth and
                    tx_log.topics[0] == STABILITY_POOL_GAIN_WITHDRAW
                ) or (
                    event.asset == self.lqty and
                    event.balance.amount == collected_lqty and
                    tx_log.topics[0] == STABILITY_POOL_LQTY_PAID
                )
            ):
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_LIQUITY
                event.notes = f"Collect {event.balance.amount} {event.asset.resolve_to_crypto_asset().symbol} from liquity's stability pool"  # noqa: E501
        return None, []

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> Dict[ChecksumEvmAddress, Tuple[Any, ...]]:
        return {
            ACTIVE_POOL: (self._decode_trove_operations,),
            STABILITY_POOL: (self._decode_stability_pool_event,),
        }

    def counterparties(self) -> List[str]:
        return [CPT_LIQUITY]
