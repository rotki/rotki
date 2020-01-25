import pytest

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.exchanges.manager import ExchangeManager
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.fval import FVal
from rotkehlchen.history import PriceHistorian, TradesHistorian

TEST_HISTORY_DATA_START = "01/01/2015"


@pytest.fixture
def cryptocompare(accounting_data_dir, database):
    return Cryptocompare(data_directory=accounting_data_dir, database=database)


@pytest.fixture
def price_historian(
        accounting_data_dir,
        inquirer,  # pylint: disable=unused-argument
        should_mock_price_queries,
        mocked_price_queries,
        cryptocompare,
):
    # Since this is a singleton and we want it initialized everytime the fixture
    # is called make sure its instance is always starting from scratch
    PriceHistorian._PriceHistorian__instance = None
    historian = PriceHistorian(
        data_directory=accounting_data_dir,
        history_date_start=TEST_HISTORY_DATA_START,
        cryptocompare=cryptocompare,
    )
    if should_mock_price_queries:
        def mock_historical_price_query(from_asset, to_asset, timestamp):
            if from_asset == to_asset:
                return FVal(1)

            try:
                price = mocked_price_queries[from_asset.identifier][to_asset.identifier][timestamp]
            except KeyError:
                raise AssertionError(
                    f'No mocked price found from {from_asset.identifier} to '
                    f'{to_asset.identifier} at {timestamp}',
                )

            return price

        historian.query_historical_price = mock_historical_price_query

    return historian


@pytest.fixture
def trades_historian(accounting_data_dir, function_scope_messages_aggregator, etherscan):
    database = DBHandler(accounting_data_dir, '123', function_scope_messages_aggregator)
    exchange_manager = ExchangeManager(msg_aggregator=function_scope_messages_aggregator)
    historian = TradesHistorian(
        user_directory=accounting_data_dir,
        db=database,
        msg_aggregator=function_scope_messages_aggregator,
        exchange_manager=exchange_manager,
        etherscan=etherscan,
    )
    return historian
