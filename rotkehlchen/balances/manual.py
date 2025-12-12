from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance, BalanceType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.types import Location

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
            price = Inquirer.find_main_currency_prices(
                [entry.asset],
            ).get(entry.asset, ZERO_PRICE) if not entry.asset_is_missing else ZERO_PRICE
        except RemoteError as e:
            db.msg_aggregator.add_warning(
                f'Could not find price for {entry.asset.identifier} to '
                f'during manually tracked balance querying due to {e!s}',
            )
            price = ZERO_PRICE

        balances_with_value.append(ManuallyTrackedBalanceWithValue(
            identifier=entry.identifier,
            asset=entry.asset,
            label=entry.label,
            value=Balance(amount=entry.amount, value=price * entry.amount),
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
