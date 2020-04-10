from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional

from rotkehlchen.assets.asset import Asset
from rotkehlchen.errors import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.typing import Location

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class ManuallyTrackedBalance(NamedTuple):
    asset: Asset
    label: str
    amount: FVal
    location: Location
    tags: Optional[List[str]]


class ManuallyTrackedBalanceWithValue(NamedTuple):
    # NamedTuples can't use inheritance. Make sure this has same fields as
    # ManuallyTrackedBalance until usd_value
    asset: Asset
    label: str
    amount: FVal
    location: Location
    tags: Optional[List[str]]
    usd_value: FVal


def get_manually_tracked_balances(db: 'DBHandler') -> List[ManuallyTrackedBalanceWithValue]:
    """Gets the manually tracked balances

    May raise:
    - RemoteError if there is a problem querying for the current price of an asset
    """
    balances = db.get_manually_tracked_balances()
    balances_with_value = []
    for entry in balances:
        price = Inquirer().find_usd_price(entry.asset)
        # https://github.com/python/mypy/issues/2582 --> for the type ignore below
        balances_with_value.append(ManuallyTrackedBalanceWithValue(  # type: ignore
            **entry._asdict(),
            usd_value=price * entry.amount,
        ))

    return balances_with_value


def add_manually_tracked_balances(
        db: 'DBHandler',
        data: List[ManuallyTrackedBalance],
) -> None:
    """Adds manually tracked balances

    May raise:
    - InputError if any of the given balance entry labels already exist in the DB
    - TagConstraintError if any of the given manually tracked balances contain unknown tags.
    """
    if len(data) == 0:
        raise InputError('Empty list of manually tracked balances to add was given')
    db.ensure_tags_exist(
        given_data=data,
        action='adding',
        data_type='manually tracked balances',
    )
    db.add_manually_tracked_balances(data=data)


def edit_manually_tracked_balances(db: 'DBHandler', data: List[ManuallyTrackedBalance]) -> None:
    """Edits manually tracked balances

    May raise:
    - InputError if the given balances list is empty or if
    any of the balance entry labels to edit do not exist in the DB.
    - TagConstraintError if any of the given balance data contain unknown tags.
    """
    if len(data) == 0:
        raise InputError('Empty list of manually tracked balances to edit was given')
    db.ensure_tags_exist(
        given_data=data,
        action='editing',
        data_type='manually tracked balances',
    )
    db.edit_manually_tracked_balances(data)


def account_for_manually_tracked_balances(
        db: 'DBHandler',
        balances: Dict[str, Any],
) -> Dict[str, Any]:
    """Given the big balances mapping adds to it all manually tracked balances"""
    manually_tracked_balances = get_manually_tracked_balances(db)
    for m_entry in manually_tracked_balances:
        location_str = str(m_entry.location)
        if location_str not in balances:
            balances[location_str] = {}
            balances[location_str][m_entry.asset.identifier] = {
                'amount': m_entry.amount,
                'usd_value': m_entry.usd_value,
            }
        else:
            if m_entry.asset.identifier not in balances[location_str]:
                balances[location_str][m_entry.asset.identifier] = {
                    'amount': m_entry.amount,
                    'usd_value': m_entry.usd_value,
                }
            else:
                old_amount = balances[location_str][m_entry.asset.identifier]['amount']
                old_usd_value = balances[location_str][m_entry.asset.identifier]['usd_value']
                balances[location_str][m_entry.asset.identifier] = {
                    'amount': old_amount + m_entry.amount,
                    'usd_value': old_usd_value + m_entry.usd_value,
                }

    return balances
