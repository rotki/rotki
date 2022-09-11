import pytest
import requests

from rotkehlchen.constants import ONE
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.db.filtering import ETHTransactionsFilterQuery
from rotkehlchen.tests.utils.api import api_url_for, assert_simple_ok_response
from rotkehlchen.tests.utils.exchanges import (
    check_saved_events_for_exchange,
    mock_exchange_data_in_db,
)
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.types import (
    BlockchainAccountData,
    EvmTransaction,
    Location,
    SupportedBlockchain,
    make_evm_tx_hash,
)


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
    addr1 = make_ethereum_address()
    db = DBEthTx(rotki.data.db)
    with rotki.data.db.user_write() as cursor:
        rotki.data.db.add_blockchain_accounts(
            write_cursor=cursor,
            blockchain=SupportedBlockchain.ETHEREUM,
            account_data=[
                BlockchainAccountData(address=addr1),
            ],
        )
        db.add_ethereum_transactions(
            cursor,
            [EvmTransaction(
                tx_hash=make_evm_tx_hash(bytes()),
                timestamp=1,
                block_number=1,
                from_address=addr1,
                to_address=make_ethereum_address(),
                value=ONE,
                gas=ONE,
                gas_price=ONE,
                gas_used=ONE,
                input_data=bytes(),
                nonce=1,
            )],
            relevant_address=addr1,
        )
        filter_ = ETHTransactionsFilterQuery.make()

        result, filter_count = db.get_ethereum_transactions_and_limit_info(cursor, filter_, True)
        assert len(result) == 1
        assert filter_count == 1
        response = requests.delete(
            api_url_for(
                rotkehlchen_api_server,
                'ethereumtransactionsresource',
            ),
        )
        assert_simple_ok_response(response)
        result, filter_count = db.get_ethereum_transactions_and_limit_info(cursor, filter_, True)
    assert len(result) == 0
    assert filter_count == 0
