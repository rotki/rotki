from typing import List, Union

from rotkehlchen.accounting.ledger_actions import LedgerAction
from rotkehlchen.accounting.structures import DefiEvent, HistoryBaseEntry
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.trades import AMMTrade
from rotkehlchen.exchanges.data_structures import AssetMovement, Loan, MarginPosition, Trade
from rotkehlchen.types import Timestamp

TaxableAction = Union[  # TODO: At this point we perhaps should create an interface/superclass
    Trade,
    AssetMovement,
    MarginPosition,
    Loan,
    DefiEvent,
    AMMTrade,
    LedgerAction,
    HistoryBaseEntry,
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
                DefiEvent,
                AMMTrade,
                LedgerAction,
            ),
    ):
        return action.timestamp
    if isinstance(action, HistoryBaseEntry):
        return action.get_timestamp_in_sec()
    if isinstance(action, (MarginPosition, Loan)):
        return action.close_time
    # else
    raise AssertionError(f'TaxableAction of unknown type {type(action)} encountered')


def action_get_type(action: TaxableAction) -> str:
    if isinstance(action, (AMMTrade, Trade)):
        return 'trade'
    if isinstance(action, AssetMovement):
        return 'asset_movement'
    if isinstance(action, MarginPosition):
        return 'margin_position'
    if isinstance(action, Loan):
        return 'loan'
    if isinstance(action, DefiEvent):
        return 'defi_event'
    if isinstance(action, LedgerAction):
        return 'ledger_action'
    if isinstance(action, HistoryBaseEntry):
        return 'history_base_entry'
    # else
    raise AssertionError(f'TaxableAction of unknown type {type(action)} encountered')


def action_get_identifier(action: TaxableAction) -> str:
    """Get a unique identifier from a taxable action if possible"""
    if isinstance(
        action,
        (
            AMMTrade,
            Trade,
            AssetMovement,
            MarginPosition,
            LedgerAction,
            HistoryBaseEntry,
        ),
    ):
        return str(action.identifier)
    if isinstance(action, Loan):
        return 'loan_' + str(action.close_time)
    if isinstance(action, DefiEvent):
        return str(action)
    # else
    raise AssertionError(f'TaxableAction of unknown type {type(action)} encountered')


def action_get_assets(action: TaxableAction) -> List[Asset]:
    """Gets the assets involved in the action

    May raise:
     - UnknownAsset, UnsupportedAsset due to the trade pair's assets
     - UnprocessableTradePair: If a trade's pair can't be processed

    """
    if isinstance(action, (Trade, AMMTrade)):
        return [action.base_asset, action.quote_asset]
    if isinstance(action, (AssetMovement, LedgerAction)):
        return [action.asset]
    if isinstance(action, DefiEvent):
        assets = set()
        if action.got_asset is not None:
            assets.add(action.got_asset)
        if action.spent_asset is not None:
            assets.add(action.spent_asset)
        if action.pnl is not None:
            for entry in action.pnl:
                assets.add(entry.asset)

        return list(assets)
    if isinstance(action, MarginPosition):
        return [action.pl_currency]
    if isinstance(action, Loan):
        return [action.currency]
    if isinstance(action, HistoryBaseEntry):
        return [action.asset]
    # else
    raise AssertionError(f'TaxableAction of unknown type {type(action)} encountered')
