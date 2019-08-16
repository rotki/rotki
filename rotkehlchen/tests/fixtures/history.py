import pytest

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.fval import FVal
from rotkehlchen.history import PriceHistorian, TradesHistorian

TEST_HISTORY_DATA_START = "01/01/2015"


@pytest.fixture
def price_historian(
        accounting_data_dir,
        inquirer,  # pylint: disable=unused-argument
        should_mock_price_queries,
        mocked_price_queries,
):
    # Since this is a singleton and we want it initialized everytime the fixture
    # is called make sure its instance is always starting from scratch
    PriceHistorian._PriceHistorian__instance = None
    historian = PriceHistorian(
        data_directory=accounting_data_dir,
        history_date_start=TEST_HISTORY_DATA_START,
        cryptocompare=Cryptocompare(data_directory=accounting_data_dir),
    )
    if should_mock_price_queries:
        def mock_historical_price_query(from_asset, to_asset, timestamp):
            if from_asset == to_asset:
                return FVal(1)
            return mocked_price_queries[from_asset][to_asset][timestamp]

        historian.query_historical_price = mock_historical_price_query

    return historian


@pytest.fixture
def trades_historian(accounting_data_dir, function_scope_messages_aggregator):
    database = DBHandler(accounting_data_dir, '123', function_scope_messages_aggregator)
    historian = TradesHistorian(
        user_directory=accounting_data_dir,
        db=database,
        eth_accounts=[],
        msg_aggregator=function_scope_messages_aggregator,
    )
    return historian


@pytest.fixture
def trades_historian_with_exchanges(
        trades_historian,
        function_scope_kraken,
        function_scope_poloniex,
        function_scope_bittrex,
        function_scope_binance,
        mock_bitmex,
):
    """Adds mock exchange objects to the trades historian fixture"""
    trades_historian.connected_exchanges = [
        function_scope_kraken,
        function_scope_poloniex,
        function_scope_bittrex,
        function_scope_binance,
        mock_bitmex,
    ]
    return trades_historian
