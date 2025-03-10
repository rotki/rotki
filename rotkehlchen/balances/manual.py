from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance, BalanceType
from rotkehlchen.assets.asset import Asset, CustomAsset
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.types import Location, Price
from rotkehlchen.logging import RotkehlchenLogsAdapter
import logging

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class _BaseManualBalance:
    identifier: int
    asset: Asset
    label: str
    location: Location
    tags: list[str] | None
    balance_type: BalanceType
    asset_is_missing: bool = field(default=False)  # set to true when the asset points to an asset that is unknown to the db  # noqa: E501


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class ManuallyTrackedBalance(_BaseManualBalance):
    amount: FVal = field(default=ZERO)


@dataclass(init=True, frozen=False)
class ManuallyTrackedBalanceWithValue(_BaseManualBalance):
    value: Balance = field(default_factory=Balance)

    def serialize(self) -> dict[str, Any]:
        result = asdict(self)  # pylint: disable=no-member
        del result['value']
        result['asset'] = result['asset']['identifier']
        return {**result, **self.value.serialize()}


def get_manually_tracked_balances(
        db: 'DBHandler',
        balance_type: BalanceType | None = None,
        include_entries_with_missing_assets: bool = False,
) -> list[ManuallyTrackedBalanceWithValue]:
    """Gets the manually tracked balances
    If `include_entries_with_missing_assets` is set to True then entries with unknown assets
    are included in the returned list.
    """
    with db.conn.read_ctx() as cursor:
        balances = db.get_manually_tracked_balances(
            cursor=cursor,
            balance_type=balance_type,
            include_entries_with_missing_assets=include_entries_with_missing_assets,
        )

    balances_with_value = []
    for entry in balances:
        try:
            price = Inquirer.find_usd_price(entry.asset) if not entry.asset_is_missing else ZERO_PRICE  # noqa: E501
        except RemoteError as e:
            db.msg_aggregator.add_warning(
                f'Could not find price for {entry.asset.identifier} during '
                f'manually tracked balance querying due to {e!s}',
            )
            price = ZERO_PRICE

        value = Balance(amount=entry.amount, usd_value=price * entry.amount)
        balances_with_value.append(ManuallyTrackedBalanceWithValue(
            identifier=entry.identifier,
            asset=entry.asset,
            label=entry.label,
            value=value,
            location=entry.location,
            tags=entry.tags,
            balance_type=entry.balance_type,
            asset_is_missing=entry.asset_is_missing,
        ))

    return balances_with_value


def add_manually_tracked_balances(
        db: 'DBHandler',
        data: list[ManuallyTrackedBalance],
) -> None:
    """Adds manually tracked balances

    May raise:
    - InputError if any of the given balance entry labels already exist in the DB
    - TagConstraintError if any of the given manually tracked balances contain unknown tags.
    """
    if len(data) == 0:
        raise InputError('Empty list of manually tracked balances to add was given')
    
    # Store prices for custom assets before adding to DB
    from rotkehlchen.inquirer import Inquirer
    from rotkehlchen.logging import RotkehlchenLogsAdapter
    import logging
    
    logger = logging.getLogger(__name__)
    log = RotkehlchenLogsAdapter(logger)
    
    for entry in data:
        try:
            if hasattr(entry, 'asset') and hasattr(entry.asset, 'get_asset_type') and entry.asset.get_asset_type() == AssetType.CUSTOM_ASSET:
                # This is a custom asset
                custom_asset = entry.asset.resolve()
                if isinstance(custom_asset, CustomAsset):
                    # For custom assets, we need to store the price
                    if hasattr(entry, 'amount') and entry.amount != 0:
                        # Get the price from the manual balance entry
                        # This is the value the user entered in the "Price" field
                        price_value = getattr(entry, '_price', None)
                        
                        if price_value is None:
                            # If we can't get the price directly, try to infer it from other attributes
                            log.warning(
                                f"Could not get price directly from manual balance entry, using amount as price",
                                asset=entry.asset.identifier
                            )
                            price_value = entry.amount
                        
                        from rotkehlchen.types import Price
                        from rotkehlchen.fval import FVal
                        
                        # Convert to Price object
                        price = Price(FVal(price_value))
                        
                        log.info(
                            f"Storing price for custom asset from manual balance",
                            asset=entry.asset.identifier,
                            price=price,
                            amount=entry.amount,
                            asset_type=getattr(custom_asset, 'custom_asset_type', 'unknown')
                        )
                        
                        # Store the price in the custom asset prices dictionary
                        # This is the key part - store the price so it's preserved during refreshes
                        Inquirer._store_custom_asset_price(entry.asset, price)
                        
                        # Also store the price directly in the _custom_asset_prices dictionary
                        # This ensures it's available even if _get_custom_asset_price doesn't find it
                        if hasattr(entry.asset, 'identifier'):
                            Inquirer._custom_asset_prices[entry.asset.identifier] = price
                            log.debug(
                                f"Directly stored price in _custom_asset_prices dictionary",
                                asset=entry.asset.identifier,
                                price=price
                            )
        except Exception as e:
            log.error(
                f"Error storing price for custom asset",
                asset=getattr(entry.asset, 'identifier', 'unknown'),
                error=str(e)
            )
    
    with db.user_write() as cursor:
        db.ensure_tags_exist(
            cursor=cursor,
            given_data=data,
            action='adding',
            data_type='manually tracked balances',
        )
        db.add_manually_tracked_balances(write_cursor=cursor, data=data)


def edit_manually_tracked_balances(db: 'DBHandler', data: list[ManuallyTrackedBalance]) -> None:
    """Edits manually tracked balances

    May raise:
    - InputError if the given balances list is empty or if
    any of the balance entry labels to edit do not exist in the DB.
    - TagConstraintError if any of the given balance data contain unknown tags.
    """
    if len(data) == 0:
        raise InputError('Empty list of manually tracked balances to edit was given')
    
    # Update prices for custom assets before editing in DB
    from rotkehlchen.inquirer import Inquirer
    from rotkehlchen.logging import RotkehlchenLogsAdapter
    import logging
    
    logger = logging.getLogger(__name__)
    log = RotkehlchenLogsAdapter(logger)
    
    for entry in data:
        try:
            if hasattr(entry, 'asset') and hasattr(entry.asset, 'get_asset_type') and entry.asset.get_asset_type() == AssetType.CUSTOM_ASSET:
                # This is a custom asset
                custom_asset = entry.asset.resolve()
                if isinstance(custom_asset, CustomAsset):
                    # For custom assets, we need to store the price
                    if hasattr(entry, 'amount') and entry.amount != 0:
                        # Get the price from the manual balance entry
                        # This is the value the user entered in the "Price" field
                        price_value = getattr(entry, '_price', None)
                        
                        if price_value is None:
                            # If we can't get the price directly, try to infer it from other attributes
                            log.warning(
                                f"Could not get price directly from manual balance entry, using amount as price",
                                asset=entry.asset.identifier
                            )
                            price_value = entry.amount
                        
                        from rotkehlchen.types import Price
                        from rotkehlchen.fval import FVal
                        
                        # Convert to Price object
                        price = Price(FVal(price_value))
                        
                        log.info(
                            f"Updating price for custom asset from manual balance edit",
                            asset=entry.asset.identifier,
                            price=price,
                            amount=entry.amount,
                            asset_type=getattr(custom_asset, 'custom_asset_type', 'unknown')
                        )
                        
                        # Store the price in the custom asset prices dictionary
                        # This is the key part - store the price so it's preserved during refreshes
                        Inquirer._store_custom_asset_price(entry.asset, price)
                        
                        # Also store the price directly in the _custom_asset_prices dictionary
                        # This ensures it's available even if _get_custom_asset_price doesn't find it
                        if hasattr(entry.asset, 'identifier'):
                            Inquirer._custom_asset_prices[entry.asset.identifier] = price
                            log.debug(
                                f"Directly stored price in _custom_asset_prices dictionary during edit",
                                asset=entry.asset.identifier,
                                price=price
                            )
        except Exception as e:
            log.error(
                f"Error updating price for custom asset",
                asset=getattr(entry.asset, 'identifier', 'unknown'),
                error=str(e)
            )
    
    with db.user_write() as cursor:
        db.ensure_tags_exist(
            cursor=cursor,
            given_data=data,
            action='editing',
            data_type='manually tracked balances',
        )
        db.edit_manually_tracked_balances(cursor, data)


def remove_manually_tracked_balances(db: 'DBHandler', ids: list[int]) -> None:
    """Edits manually tracked balances

    May raise:
    - InputError if the given list is empty or if
    any of the ids to remove do not exist in the DB.
    """
    with db.user_write() as cursor:
        db.remove_manually_tracked_balances(cursor, ids)


def account_for_manually_tracked_asset_balances(
        db: 'DBHandler',
        balances: dict[str, dict[Asset, Balance]],
) -> dict[str, Any]:
    """Given the big balances mapping adds to it all manually tracked asset balances"""
    manually_tracked_balances = get_manually_tracked_balances(
        db=db,
        balance_type=BalanceType.ASSET,
    )
    for m_entry in manually_tracked_balances:
        location_str = str(m_entry.location)
        if location_str not in balances:
            balances[location_str] = {m_entry.asset: m_entry.value}
        elif m_entry.asset not in balances[location_str]:
            balances[location_str][m_entry.asset] = m_entry.value
        else:
            balances[location_str][m_entry.asset] += m_entry.value
    return balances
