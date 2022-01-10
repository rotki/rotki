import copy
from typing import TYPE_CHECKING

from rotkehlchen.constants.assets import A_USD
from rotkehlchen.db.filtering import DBStringFilter, HistoryEventFilterQuery
from rotkehlchen.history.price import PriceHistorian

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def query_missing_prices(
    filter_query: HistoryEventFilterQuery,
    db: 'DBHandler',
) -> None:
    """Queries missing prices for HistoryBaseEntry in database based
    on the query filter used"""
    # Use a deepcopy to avoid mutations in the filter query if it is used later
    new_filter_query = copy.deepcopy(filter_query)
    new_filter_query.filters.append(DBStringFilter(and_op=True, column='usd_value', value='0'))
    entries_missing_prices = db.iterate_rows_missing_prices_in_base_entries(
        filter_query=new_filter_query,
    )
    inquirer = PriceHistorian()
    updates = []
    for identifier, amount, asset, timestamp in entries_missing_prices:
        price = inquirer.query_historical_price(
            from_asset=asset,
            to_asset=A_USD,
            timestamp=timestamp,
        )
        usd_value = amount * price
        updates.append((str(usd_value), identifier))

    query = 'UPDATE history_events SET usd_value=? WHERE identifier=?'
    cursor = db.conn.cursor()
    cursor.executemany(query, updates)
    db.update_last_write()
