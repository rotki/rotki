from typing import Any, Dict, List, Sequence, Union

from rotkehlchen.accounting.structures import DefiEvent, LedgerAction
from rotkehlchen.exchanges.data_structures import (
    AssetMovement,
    MarginPosition,
    Trade,
    trades_from_dictlist,
)
from rotkehlchen.exchanges.poloniex import process_polo_loans
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
        defi_events_list: List[DefiEvent] = None,
        ledger_actions_list: List[LedgerAction] = None,
) -> Dict[str, Any]:
    trade_history: Sequence[Union[Trade, MarginPosition]]
    # For filtering the taxable actions list we start with 0 ts so that we have the
    # full history available
    trade_history = trades_from_dictlist(
        given_trades=history_list,
        start_ts=Timestamp(0),
        end_ts=end_ts,
        location='accounting_history_process for tests',
        msg_aggregator=accountant.msg_aggregator,
    )
    # if present, append margin positions to trade history
    if margin_list:
        trade_history.extend(margin_list)  # type: ignore

    asset_movements = []
    if asset_movements_list:
        asset_movements = asset_movements_list

    loan_history = []
    if loans_list:
        loan_history = process_polo_loans(
            msg_aggregator=accountant.msg_aggregator,
            data=loans_list,
            start_ts=Timestamp(0),
            end_ts=end_ts,
        )

    eth_transactions = []
    if eth_transaction_list:
        eth_transactions = eth_transaction_list

    defi_events = []
    if defi_events_list:
        defi_events = defi_events_list

    ledger_actions = []
    if ledger_actions_list:
        ledger_actions = ledger_actions_list

    result = accountant.process_history(
        start_ts=start_ts,
        end_ts=end_ts,
        trade_history=trade_history,
        loan_history=loan_history,
        asset_movements=asset_movements,
        eth_transactions=eth_transactions,
        defi_events=defi_events,
        ledger_actions=ledger_actions,
    )
    return result
