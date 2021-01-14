from typing import Optional, Tuple, Union

from rotkehlchen.accounting.structures import DefiEvent, LedgerAction
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.trades import AMMTrade
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.exchanges.data_structures import (
    AssetMovement,
    Loan,
    MarginPosition,
    Trade,
    trade_get_assets,
)
from rotkehlchen.typing import EthereumTransaction, Timestamp

TaxableAction = Union[  # TODO: At this point we perhaps should create an interface/superclass
    Trade,
    AssetMovement,
    EthereumTransaction,
    MarginPosition,
    Loan,
    DefiEvent,
    AMMTrade,
    LedgerAction,
]


def action_get_timestamp(action: TaxableAction) -> Timestamp:
    """
    Returns the timestamp of the particular action depending on its type

    Can Raise assertion error if the action is not of any expected type
    """
    if isinstance(
            action, (
                Trade,
                AssetMovement,
                EthereumTransaction,
                DefiEvent,
                AMMTrade,
                LedgerAction,
            ),
    ):
        return action.timestamp
    if isinstance(action, (MarginPosition, Loan)):
        return action.close_time
    # else
    raise AssertionError(f'TaxableAction of unknown type {type(action)} encountered')


def action_get_type(action: TaxableAction) -> str:
    if isinstance(action, (AMMTrade, Trade)):
        return 'trade'
    if isinstance(action, AssetMovement):
        return 'asset_movement'
    if isinstance(action, EthereumTransaction):
        return 'ethereum_transaction'
    if isinstance(action, MarginPosition):
        return 'margin_position'
    if isinstance(action, Loan):
        return 'loan'
    if isinstance(action, DefiEvent):
        return 'defi_event'
    if isinstance(action, LedgerAction):
        return 'ledger_action'
    # else
    raise AssertionError(f'TaxableAction of unknown type {type(action)} encountered')


def action_get_assets(
        action: TaxableAction,
) -> Tuple[Asset, Optional[Asset]]:
    if isinstance(action, (Trade, AMMTrade)):
        return trade_get_assets(action)
    if isinstance(action, (AssetMovement, DefiEvent, LedgerAction)):
        return action.asset, None
    if isinstance(action, EthereumTransaction):
        return A_ETH, None
    if isinstance(action, MarginPosition):
        return action.pl_currency, None
    if isinstance(action, Loan):
        return action.currency, None
    # else
    raise AssertionError(f'TaxableAction of unknown type {type(action)} encountered')
