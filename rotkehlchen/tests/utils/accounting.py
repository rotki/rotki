from typing import Any, Dict, List

from rotkehlchen.exchanges.data_structures import (
    AssetMovement,
    MarginPosition,
    trades_from_dictlist,
)
from rotkehlchen.exchanges.poloniex import process_polo_loans
from rotkehlchen.transactions import transactions_from_dictlist
from rotkehlchen.typing import Timestamp


def accounting_history_process(
        accountant,
        start_ts: Timestamp,
        end_ts: Timestamp,
        history_list: List[Dict],
        margin_list: List[MarginPosition] = None,
        loans_list: List[Dict] = None,
        asset_movements_list: List[AssetMovement] = None,
        eth_transaction_list: List[Dict] = None,
) -> Dict[str, Any]:
    # For filtering the taxable actions list we start with 0 ts so that we have the
    # full history available
    trade_history = trades_from_dictlist(
        given_trades=history_list,
        start_ts=0,
        end_ts=end_ts,
        location='accounting_history_process for tests',
        msg_aggregator=accountant.msg_aggregator,
    )
    # if present, append margin positions to trade history
    if margin_list:
        trade_history.extend(margin_list)

    asset_movements = []
    if asset_movements_list:
        asset_movements = asset_movements_list

    loan_history = list()
    if loans_list:
        loan_history = process_polo_loans(
            msg_aggregator=accountant.msg_aggregator,
            data=loans_list,
            start_ts=0,
            end_ts=end_ts,
        )

    eth_transactions = list()
    if eth_transaction_list:
        eth_transactions = transactions_from_dictlist(
            given_transactions=eth_transaction_list,
            start_ts=0,
            end_ts=end_ts,
        )
    result = accountant.process_history(
        start_ts=start_ts,
        end_ts=end_ts,
        trade_history=trade_history,
        loan_history=loan_history,
        asset_movements=asset_movements,
        eth_transactions=eth_transactions,
    )
    return result
