from typing import List

from rotkehlchen.accounting.structures import (
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.contracts import PICKLE_CONTRACTS
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.constants.ethereum import ZERO_ADDRESS
from rotkehlchen.types import EthereumTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int


def maybe_enrich_pickle_transfers(
    token: EthereumToken,  # pylint: disable=unused-argument
    tx_log: EthereumTxReceiptLog,
    transaction: EthereumTransaction,
    event: HistoryBaseEntry,
    action_items: List[ActionItem],  # pylint: disable=unused-argument
) -> bool:
    """Enrich tranfer transactions to address for jar deposits and withdrawals"""
    if not (
        hex_or_bytes_to_address(tx_log.topics[2]) in PICKLE_CONTRACTS or
        hex_or_bytes_to_address(tx_log.topics[1]) in PICKLE_CONTRACTS or
        tx_log.address in PICKLE_CONTRACTS
    ):
        return False

    if (  # Deposit give asset
        event.event_type == HistoryEventType.SPEND and
        event.event_subtype == HistoryEventSubType.NONE and
        event.location_label == transaction.from_address and
        hex_or_bytes_to_address(tx_log.topics[2]) in PICKLE_CONTRACTS
    ):
        if EthereumToken(tx_log.address) != event.asset:
            return True
        amount_raw = hex_or_bytes_to_int(tx_log.data)
        amount = asset_normalized_value(amount=amount_raw, asset=event.asset)
        if event.balance.amount == amount:  # noqa: E501
            event.event_type = HistoryEventType.STAKING
            event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
            event.counterparty = 'pickle finance'
            event.notes = f'Deposit {event.balance.amount} {event.asset.symbol} in pickle contract'  # noqa: E501
    elif (  # Deposit receive wrapped
        event.event_type == HistoryEventType.RECEIVE and
        event.event_subtype == HistoryEventSubType.NONE and
        tx_log.address in PICKLE_CONTRACTS
    ):
        amount_raw = hex_or_bytes_to_int(tx_log.data)
        amount = asset_normalized_value(amount=amount_raw, asset=event.asset)
        if event.balance.amount == amount:  # noqa: E501
            event.event_type = HistoryEventType.STAKING
            event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
            event.counterparty = 'pickle finance'
            event.notes = f'Recive {event.balance.amount} {event.asset.symbol} after depositing in pickle contract'  # noqa: E501
    elif (  # Withdraw send wrapped
        event.event_type == HistoryEventType.SPEND and
        event.event_subtype == HistoryEventSubType.NONE and
        event.location_label == transaction.from_address and
        hex_or_bytes_to_address(tx_log.topics[2]) == ZERO_ADDRESS and
        hex_or_bytes_to_address(tx_log.topics[1]) in transaction.from_address
    ):
        if event.asset != EthereumToken(tx_log.address):
            return True
        amount_raw = hex_or_bytes_to_int(tx_log.data)
        amount = asset_normalized_value(amount=amount_raw, asset=event.asset)
        if event.balance.amount == amount:  # noqa: E501
            event.event_type = HistoryEventType.STAKING
            event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
            event.counterparty = 'pickle finance'
            event.notes = f'Return {event.balance.amount} {event.asset.symbol} to the pickle contract'  # noqa: E501
    elif (  # Withdraw receive asset
        event.event_type == HistoryEventType.RECEIVE and
        event.event_subtype == HistoryEventSubType.NONE and
        event.location_label == transaction.from_address and
        hex_or_bytes_to_address(tx_log.topics[2]) == transaction.from_address and
        hex_or_bytes_to_address(tx_log.topics[1]) in PICKLE_CONTRACTS
    ):
        if event.asset != EthereumToken(tx_log.address):
            return True
        amount_raw = hex_or_bytes_to_int(tx_log.data)
        amount = asset_normalized_value(amount=amount_raw, asset=event.asset)
        if event.balance.amount == amount:  # noqa: E501
            event.event_type = HistoryEventType.STAKING
            event.event_subtype = HistoryEventSubType.REMOVE_ASSET
            event.counterparty = 'pickle finance'
            event.notes = f'Unstake {event.balance.amount} {event.asset.symbol} from the pickle contract'  # noqa: E501

    return True
