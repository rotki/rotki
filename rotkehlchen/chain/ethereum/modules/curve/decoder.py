from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from rotkehlchen.accounting.structures.base import (
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.defi.curve_pools import get_curve_pools
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.types import ChecksumEthAddress, EthereumTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address

from .constants import CPT_CURVE

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.user_messages import MessagesAggregator


ADD_LIQUIDITY = b'B?d\x95\xa0\x8f\xc6RB\\\xf4\xed\r\x1f\x9e7\xe5q\xd9\xb9R\x9b\x1c\x1c#\xcc\xe7\x80\xb2\xe7\xdf\r'  # noqa: E501
ADD_LIQUIDITY_2_ASSETS = b'&\xf5Z\x85\x08\x1d$\x97N\x85\xc6\xc0\x00E\xd0\xf0E9\x91\xe9Xs\xf5+\xff\r!\xaf@y\xa7h'  # noqa: E501
REMOVE_LIQUIDITY = b"Z\xd0V\xf2\xe2\x8a\x8c\xec# \x15@k\x846h\xc1\xe3l\xdaY\x81'\xec;\x8cY\xb8\xc7's\xa0"  # noqa: E501
REMOVE_ONE = b'\x9e\x96\xdd;\x99z*%~\xecM\xf9\xbbn\xafbn m\xf5\xf5C\xbd\x966\x82\xd1C0\x0b\xe3\x10'  # noqa: E501


class CurveDecoder(DecoderInterface):  # lgtm[py/missing-call-to-init]

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',  # pylint: disable=unused-argument
            base_tools: 'BaseDecoderTools',  # pylint: disable=unused-argument
            msg_aggregator: 'MessagesAggregator',  # pylint: disable=unused-argument
    ) -> None:
        super().__init__(
            ethereum_manager=ethereum_manager,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        curve_pools = get_curve_pools()
        self.curve_pools = {curve_pool.pool_address for curve_pool in curve_pools.values()}
        self.curve_lps = set(curve_pools.keys())

    def _decode_curve_remove_events(
        self,
        tx_log: EthereumTxReceiptLog,
        transaction: EthereumTransaction,
        decoded_events: List[HistoryBaseEntry],
        user_address: ChecksumEthAddress,
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        """Decode information related to withdrawing assets from curve pools"""
        for event in decoded_events:
            if (  # Withdraw eth
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_ETH and
                event.location_label == user_address
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_CURVE
                event.notes = f'Remove {event.balance.amount} {event.asset.symbol} from the curve pool'  # noqa: E501
            elif (  # Withdraw send wrapped
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == transaction.from_address and
                user_address == event.location_label
            ):
                event.event_type = HistoryEventType.SPEND
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = CPT_CURVE
                event.notes = f'Return {event.balance.amount} {event.asset.symbol}'  # noqa: E501
            elif (  # Withdraw receive asset
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == transaction.from_address and
                user_address == event.location_label and
                tx_log.address in self.curve_pools
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_CURVE
                event.notes = f'Remove {event.balance.amount} {event.asset.symbol} from the curve pool'  # noqa: E501
        return None, None

    def _decode_curve_deposit_events(
        self,
        tx_log: EthereumTxReceiptLog,
        decoded_events: List[HistoryBaseEntry],
        user_address: ChecksumEthAddress,
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        """Decode information related to depositing assets in curve pools"""
        for event in decoded_events:
            if (  # Deposit ETH
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_ETH and
                event.location_label == user_address
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_CURVE
                event.notes = f'Deposit {event.balance.amount} {event.asset.symbol} in curve pool'  # noqa: E501
            elif (  # deposit give asset
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_address and
                tx_log.address in self.curve_pools
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_CURVE
                event.notes = f'Deposit {event.balance.amount} {event.asset.symbol} in curve pool'  # noqa: E501
            elif (  # Deposit receive pool token
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_address and
                tx_log.address in self.curve_pools
            ):
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = CPT_CURVE
                event.notes = f'Receive {event.balance.amount} {event.asset.symbol} after depositing in curve pool'  # noqa: E501
        return None, None

    def _decode_curve_events(  # pylint: disable=no-self-use
        self,
        tx_log: EthereumTxReceiptLog,
        transaction: EthereumTransaction,
        decoded_events: List[HistoryBaseEntry],
        all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
        action_items: Optional[List[ActionItem]],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        if tx_log.topics[0] in (REMOVE_LIQUIDITY, REMOVE_ONE):
            user_address = hex_or_bytes_to_address(tx_log.topics[1])
            self._decode_curve_remove_events(
                tx_log=tx_log,
                transaction=transaction,
                decoded_events=decoded_events,
                user_address=user_address,
            )
        elif tx_log.topics[0] in (ADD_LIQUIDITY, ADD_LIQUIDITY_2_ASSETS):
            user_address = hex_or_bytes_to_address(tx_log.topics[1])
            self._decode_curve_deposit_events(
                tx_log=tx_log,
                decoded_events=decoded_events,
                user_address=user_address,
            )

        return None, None

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> Dict[ChecksumEthAddress, Tuple[Any, ...]]:
        return {
            address: (self._decode_curve_events,)
            for address in self.curve_pools
        }

    def counterparties(self) -> List[str]:
        return [CPT_CURVE]
