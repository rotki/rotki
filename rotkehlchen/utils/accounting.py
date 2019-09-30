from typing import Optional, Tuple, Union

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.exchanges.data_structures import (
    AssetMovement,
    Loan,
    MarginPosition,
    Trade,
    trade_get_assets,
)
from rotkehlchen.transactions import EthereumTransaction
from rotkehlchen.typing import Timestamp

TaxableAction = Union[Trade, AssetMovement, EthereumTransaction, MarginPosition, Loan]


def action_get_timestamp(action: TaxableAction) -> Timestamp:
    """
    Returns the timestamp of the particular action depending on its type

    Can Raise assertion error if the action is not of any expected type
    """
    if isinstance(action, (Trade, AssetMovement, EthereumTransaction)):
        return action.timestamp
    elif isinstance(action, (MarginPosition, Loan)):
        return action.close_time

    raise AssertionError(f'TaxableAction of unknown type {type(action)} encountered')


def action_get_type(action: TaxableAction) -> str:
    if isinstance(action, Trade):
        return 'trade'
    elif isinstance(action, AssetMovement):
        return 'asset_movement'
    elif isinstance(action, EthereumTransaction):
        return 'ethereum_transaction'
    elif isinstance(action, MarginPosition):
        return 'margin_position'
    elif isinstance(action, Loan):
        return 'loan'

    raise AssertionError(f'TaxableAction of unknown type {type(action)} encountered')


def action_get_assets(
        action: TaxableAction,
) -> Tuple[Asset, Optional[Asset]]:
    if isinstance(action, Trade):
        return trade_get_assets(action)
    elif isinstance(action, AssetMovement):
        return action.asset, None
    elif isinstance(action, EthereumTransaction):
        return A_ETH, None
    elif isinstance(action, MarginPosition):
        return action.pl_currency, None
    elif isinstance(action, Loan):
        return action.currency, None

    raise AssertionError(f'TaxableAction of unknown type {type(action)} encountered')
