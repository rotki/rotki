import pytest
import requests

from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import api_url_for, assert_simple_ok_response
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.typing import (
    AssetAmount,
    EthereumTransaction,
    Fee,
    Location,
    Price,
    Timestamp,
    TradeType,
)


def mock_exchange_data_in_db(exchange_locations, rotki) -> None:
    db = rotki.data.db
    for exchange_location in exchange_locations:
        db.add_trades([Trade(
            timestamp=Timestamp(1),
            location=exchange_location,
            base_asset=A_BTC,
            quote_asset=A_ETH,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal(1)),
            rate=Price(FVal(1)),
            fee=Fee(FVal('0.1')),
            fee_currency=A_ETH,
            link='foo',
            notes='boo',
        )])
        db.update_used_query_range(name=f'{str(exchange_location)}_trades', start_ts=0, end_ts=9999)  # noqa: E501
        db.update_used_query_range(name=f'{str(exchange_location)}_margins', start_ts=0, end_ts=9999)  # noqa: E501
        db.update_used_query_range(name=f'{str(exchange_location)}_asset_movements', start_ts=0, end_ts=9999)  # noqa: E501


def check_saved_events_for_exchange(
        exchange_location: Location,
        db: DBHandler,
        should_exist: bool,
) -> None:
    trades = db.get_trades(location=exchange_location)
    trades_range = db.get_used_query_range(f'{str(exchange_location)}_trades')
    margins_range = db.get_used_query_range(f'{str(exchange_location)}_margins')
    movements_range = db.get_used_query_range(f'{str(exchange_location)}_asset_movements')
    if should_exist:
        assert trades_range is not None
        assert margins_range is not None
        assert movements_range is not None
        assert len(trades) != 0
    else:
        assert trades_range is None
        assert margins_range is None
        assert movements_range is None
        assert len(trades) == 0


@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_purge_all_exchange_data(rotkehlchen_api_server_with_exchanges, added_exchanges):
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    mock_exchange_data_in_db(added_exchanges, rotki)
    for exchange_location in added_exchanges:
        check_saved_events_for_exchange(exchange_location, rotki.data.db, should_exist=True)
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "exchangesdataresource",
        ),
    )
    assert_simple_ok_response(response)
    for exchange_location in added_exchanges:
        check_saved_events_for_exchange(exchange_location, rotki.data.db, should_exist=False)


@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_purge_single_exchange_data(rotkehlchen_api_server_with_exchanges, added_exchanges):
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    target_exchange = Location.POLONIEX
    mock_exchange_data_in_db(added_exchanges, rotki)
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "named_exchanges_data_resource",
            location=target_exchange,
        ),
    )
    assert_simple_ok_response(response)
    check_saved_events_for_exchange(target_exchange, rotki.data.db, should_exist=False)
    check_saved_events_for_exchange(Location.BINANCE, rotki.data.db, should_exist=True)


def test_purge_ethereum_transaction_data(rotkehlchen_api_server):
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = rotki.data.db
    db.add_ethereum_transactions(
        [EthereumTransaction(
            tx_hash=bytes(),
            timestamp=1,
            block_number=1,
            from_address=make_ethereum_address(),
            to_address=make_ethereum_address(),
            value=FVal(1),
            gas=FVal(1),
            gas_price=FVal(1),
            gas_used=FVal(1),
            input_data=bytes(),
            nonce=1,
        )],
        from_etherscan=True,
    )
    assert len(db.get_ethereum_transactions()) == 1
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            "ethereumtransactionsresource",
        ),
    )
    assert_simple_ok_response(response)
    assert len(db.get_ethereum_transactions()) == 0
