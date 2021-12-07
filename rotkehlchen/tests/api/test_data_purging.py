import pytest
import requests

from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.db.filtering import ETHTransactionsFilterQuery
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import api_url_for, assert_simple_ok_response
from rotkehlchen.tests.utils.exchanges import (
    check_saved_events_for_exchange,
    mock_exchange_data_in_db,
)
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.typing import EthereumTransaction, Location


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
    db = DBEthTx(rotki.data.db)
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
    )
    filter_ = ETHTransactionsFilterQuery.make()

    result, filter_count = db.get_ethereum_transactions(filter_)
    assert len(result) == 1
    assert filter_count == 1
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            "ethereumtransactionsresource",
        ),
    )
    assert_simple_ok_response(response)
    result, filter_count = db.get_ethereum_transactions(filter_)
    assert len(result) == 0
    assert filter_count == 0
