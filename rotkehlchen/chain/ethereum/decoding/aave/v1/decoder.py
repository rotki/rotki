from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from rotkehlchen.accounting.structures import (
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.modules.aave.common import asset_to_atoken
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, ethaddress_to_asset
from rotkehlchen.constants.ethereum import AAVE_V1_LENDING_POOL
from rotkehlchen.typing import ChecksumEthAddress, EthereumTransaction
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.ethereum.manager import EthereumManager

DEPOSIT = b'\xc1,W\xb1\xc7:,:.\xa4a>\x94v\xab\xb3\xd8\xd1F\x85z\xabs)\xe2BC\xfbYq\x0c\x82'


class Aavev1Decoder(DecoderInterface):
    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum_manager = ethereum_manager
        self.base = base_tools
        self.msg_aggregator = msg_aggregator

    def decode_pool_event(  # pylint: disable=no-self-use
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        if tx_log.topics[0] != DEPOSIT:
            return None, None

        reserve_address = hex_or_bytes_to_address(tx_log.topics[1])
        reserve_asset = ethaddress_to_asset(reserve_address)
        if reserve_asset is None:
            return None, None
        user_address = hex_or_bytes_to_address(tx_log.topics[2])
        raw_amount = hex_or_bytes_to_int(tx_log.data[0:32])
        amount = asset_normalized_value(raw_amount, reserve_asset)
        atoken = asset_to_atoken(reserve_asset, 1)
        if atoken is None:
            return None, None

        for event in decoded_events:
            if event.event_type == HistoryEventType.SPEND and event.location_label == user_address and amount == event.balance.amount and reserve_asset == event.asset:  # noqa: E501
                # find the deposit transfer (can also be an ETH internal transfer)
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.STAKING_DEPOSIT_ASSET
                event.counterparty = 'aave-v1'
                event.notes = f'Deposit {amount} {reserve_asset.symbol} to aave-v1 from {event.location_label}'  # noqa: E501
            elif event.event_type == HistoryEventType.RECEIVE and event.location_label == user_address and amount == event.balance.amount and atoken == event.asset:  # noqa: E501
                # find the receive aToken transfer
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = 'aave-v1'
                event.notes = f'Receive {amount} {atoken.symbol} from aave-v1 for {event.location_label}'  # noqa: E501

        return None, None

    def addresses_to_decoders(self) -> Dict[ChecksumEthAddress, Tuple[Any, ...]]:
        return {
            AAVE_V1_LENDING_POOL.address: (self.decode_pool_event,),  # noqa: E501
        }
