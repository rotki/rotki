import pytest
import requests

from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.zksync_lite.structures import (
    ZKSyncLiteSwapData,
    ZKSyncLiteTransaction,
    ZKSyncLiteTXType,
)
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_DAI, A_ETH
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import api_url_for, assert_simple_ok_response
from rotkehlchen.tests.utils.exchanges import (
    check_saved_events_for_exchange,
    mock_exchange_data_in_db,
)
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import ChainID, EvmTransaction, Fee, Location, SupportedBlockchain


@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_purge_all_exchange_data(rotkehlchen_api_server_with_exchanges, added_exchanges):
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    exchange_locations = added_exchanges + (Location.FTX,)  # Also check that data for dead exchanges is purged  # noqa: E501
    mock_exchange_data_in_db(exchange_locations, rotki)
    for exchange_location in exchange_locations:
        check_saved_events_for_exchange(exchange_location, rotki.data.db, should_exist=True)
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'exchangesdataresource',
        ),
    )
    assert_simple_ok_response(response)
    for exchange_location in exchange_locations:
        check_saved_events_for_exchange(exchange_location, rotki.data.db, should_exist=False)


@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_purge_single_exchange_data(rotkehlchen_api_server_with_exchanges, added_exchanges):
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    target_exchange = Location.POLONIEX
    mock_exchange_data_in_db(added_exchanges, rotki)
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'named_exchanges_data_resource',
            location=target_exchange,
        ),
    )
    assert_simple_ok_response(response)
    check_saved_events_for_exchange(target_exchange, rotki.data.db, should_exist=False)
    check_saved_events_for_exchange(Location.BINANCE, rotki.data.db, should_exist=True)


def test_purge_blockchain_transaction_data(rotkehlchen_api_server):
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    addr1 = make_evm_address()
    db = DBEvmTx(rotki.data.db)
    with rotki.data.db.user_write() as write_cursor:
        rotki.data.db.add_blockchain_accounts(
            write_cursor=write_cursor,
            account_data=[
                BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address=addr1),
                BlockchainAccountData(chain=SupportedBlockchain.OPTIMISM, address=addr1),
                BlockchainAccountData(chain=SupportedBlockchain.GNOSIS, address=addr1),
                BlockchainAccountData(chain=SupportedBlockchain.ZKSYNC_LITE, address=addr1),
            ],
        )
        for chain_id in (ChainID.ETHEREUM, ChainID.OPTIMISM, ChainID.GNOSIS):
            for i in range(3 if chain_id == ChainID.ETHEREUM else 2):
                db.add_evm_transactions(
                    write_cursor,
                    [EvmTransaction(
                        tx_hash=make_evm_tx_hash(),
                        chain_id=chain_id,
                        timestamp=i,
                        block_number=1,
                        from_address=addr1,
                        to_address=make_evm_address(),
                        value=ONE,
                        gas=ONE,
                        gas_price=ONE,
                        gas_used=ONE,
                        input_data=b'',
                        nonce=1,
                    )],
                    relevant_address=addr1,
                )

    with rotki.data.db.conn.read_ctx() as cursor:
        result, filter_count = db.get_evm_transactions_and_limit_info(cursor, EvmTransactionsFilterQuery.make(), True)  # noqa: E501
        assert len(result) == 7
        assert filter_count == 7
        response = requests.delete(
            api_url_for(
                rotkehlchen_api_server,
                'blockchaintransactionsresource',
            ),
            json={'chain': 'eth'},
        )
        assert_simple_ok_response(response)
        result, filter_count = db.get_evm_transactions_and_limit_info(cursor, EvmTransactionsFilterQuery.make(), True)  # noqa: E501
        assert len(result) == 4
        assert filter_count == 4
        result, filter_count = db.get_evm_transactions_and_limit_info(cursor, EvmTransactionsFilterQuery.make(chain_id=ChainID.ETHEREUM), True)  # noqa: E501
        assert len(result) == 0
        assert filter_count == 0

    def _add_zksynclitetxs():
        for i in range(2):
            rotki.chains_aggregator.zksync_lite._add_zksynctxs_db(
                transactions=[ZKSyncLiteTransaction(
                    tx_hash=make_evm_tx_hash(),
                    tx_type=ZKSyncLiteTXType.TRANSFER if i == 0 else ZKSyncLiteTXType.SWAP,
                    timestamp=1,
                    block_number=1,
                    from_address=addr1,
                    to_address=make_evm_address(),
                    asset=A_ETH,
                    amount=ONE,
                    fee=Fee(ONE),
                    swap_data=None if i == 0 else ZKSyncLiteSwapData(from_asset=A_ETH, from_amount=ONE, to_asset=A_DAI, to_amount=FVal(3000)),  # noqa: E501
                )],
            )

    def _assert_zksynclite_txs_num(tx_num, swap_num):
        with rotki.data.db.conn.read_ctx() as cursor:
            assert cursor.execute('SELECT COUNT(*) FROM zksynclite_transactions').fetchone()[0] == tx_num  # noqa: E501
            assert cursor.execute('SELECT COUNT(*) FROM zksynclite_swaps').fetchone()[0] == swap_num  # noqa: E501

    # now add a few zksync lite transactions
    _add_zksynclitetxs()
    _assert_zksynclite_txs_num(tx_num=2, swap_num=1)

    # see that purging without arguments removes the remaining
    # optimism, gnosis and zksync_lite transctions
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'blockchaintransactionsresource',
        ),
    )
    assert_simple_ok_response(response)
    with rotki.data.db.conn.read_ctx() as cursor:
        result, filter_count = db.get_evm_transactions_and_limit_info(cursor, EvmTransactionsFilterQuery.make(), True)  # noqa: E501
        assert len(result) == 0
        assert filter_count == 0
    _assert_zksynclite_txs_num(tx_num=0, swap_num=0)

    # re-add a few zksync lite transactions
    _add_zksynclitetxs()
    _assert_zksynclite_txs_num(tx_num=2, swap_num=1)

    # and check removing only zksync_lite by argument works
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'blockchaintransactionsresource',
        ),
        json={'chain': 'zksync_lite'},
    )
    assert_simple_ok_response(response)
    _assert_zksynclite_txs_num(tx_num=0, swap_num=0)
