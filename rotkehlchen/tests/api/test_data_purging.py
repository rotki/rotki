import typing
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.zksync_lite.structures import (
    ZKSyncLiteSwapData,
    ZKSyncLiteTransaction,
    ZKSyncLiteTXType,
)
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_BTC, A_DAI, A_ETH
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_proper_sync_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.exchanges import (
    check_saved_events_for_exchange,
    mock_exchange_data_in_db,
)
from rotkehlchen.tests.utils.factories import (
    make_eth_withdrawal_and_block_events,
    make_evm_address,
    make_evm_tx_hash,
    make_random_timestamp,
)
from rotkehlchen.types import (
    BTCAddress,
    ChainID,
    EvmTransaction,
    Location,
    ModuleName,
    OnlyPurgeableModuleName,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
)

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.db.drivers.gevent import DBCursor


@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_purge_all_exchange_data(
        rotkehlchen_api_server_with_exchanges: 'APIServer',
        added_exchanges: tuple[Location, ...],
) -> None:
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
def test_purge_single_exchange_data(
        rotkehlchen_api_server_with_exchanges: 'APIServer',
        added_exchanges: tuple[Location, ...],
) -> None:
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


def test_purge_blockchain_transaction_data(rotkehlchen_api_server: 'APIServer') -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    addr1 = make_evm_address()
    db, dbevents = DBEvmTx(rotki.data.db), DBHistoryEvents(rotki.data.db)
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
        dbevents.add_history_events(
            write_cursor=write_cursor,
            history=make_eth_withdrawal_and_block_events(),
        )
        for chain_id in (ChainID.ETHEREUM, ChainID.OPTIMISM, ChainID.GNOSIS):
            for i in range(3 if chain_id == ChainID.ETHEREUM else 2):
                db.add_evm_transactions(
                    write_cursor,
                    [EvmTransaction(
                        tx_hash=make_evm_tx_hash(),
                        chain_id=chain_id,
                        timestamp=Timestamp(i),
                        block_number=1,
                        from_address=addr1,
                        to_address=make_evm_address(),
                        value=1,
                        gas=1,
                        gas_price=1,
                        gas_used=1,
                        input_data=b'',
                        nonce=1,
                    )],
                    relevant_address=addr1,
                )

    with rotki.data.db.conn.read_ctx() as cursor:
        result = db.get_evm_transactions(cursor, EvmTransactionsFilterQuery.make(), True)
        assert len(result) == 7
        response = requests.delete(
            api_url_for(
                rotkehlchen_api_server,
                'blockchaintransactionsresource',
            ),
            json={'chain': 'eth'},
        )
        assert_simple_ok_response(response)
        result = db.get_evm_transactions(cursor, EvmTransactionsFilterQuery.make(), True)
        assert len(result) == 4
        result = db.get_evm_transactions(cursor, EvmTransactionsFilterQuery.make(chain_id=ChainID.ETHEREUM), True)  # noqa: E501
        assert len(result) == 0
        assert dbevents.get_history_events_count(
            cursor=cursor,
            query_filter=HistoryEventFilterQuery.make(),
        )[0] == 2  # the eth withdrawal & block events are not deleted

    def _add_zksynclitetxs(write_cursor: 'DBCursor') -> None:
        for i in range(2):
            rotki.chains_aggregator.zksync_lite._add_zksynctxs_db(
                write_cursor=write_cursor,
                transactions=[ZKSyncLiteTransaction(
                    tx_hash=make_evm_tx_hash(),
                    tx_type=ZKSyncLiteTXType.TRANSFER if i == 0 else ZKSyncLiteTXType.SWAP,
                    timestamp=Timestamp(1),
                    block_number=1,
                    from_address=addr1,
                    to_address=make_evm_address(),
                    asset=A_ETH,
                    amount=ONE,
                    fee=ONE,
                    swap_data=None if i == 0 else ZKSyncLiteSwapData(from_asset=A_ETH, from_amount=ONE, to_asset=A_DAI, to_amount=FVal(3000)),  # noqa: E501
                )],
            )

    def _assert_zksynclite_txs_num(cursor: 'DBCursor', tx_num: int, swap_num: int) -> None:
        assert cursor.execute('SELECT COUNT(*) FROM zksynclite_transactions').fetchone()[0] == tx_num  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) FROM zksynclite_swaps').fetchone()[0] == swap_num

    # now add a few zksync lite transactions
    with rotki.data.db.user_write() as write_cursor:
        _add_zksynclitetxs(write_cursor)
        _assert_zksynclite_txs_num(write_cursor, tx_num=2, swap_num=1)

    # see that purging without arguments removes the remaining
    # optimism, gnosis and zksync_lite transactions
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'blockchaintransactionsresource',
        ),
    )
    assert_simple_ok_response(response)
    with rotki.data.db.conn.read_ctx() as cursor:
        result = db.get_evm_transactions(cursor, EvmTransactionsFilterQuery.make(), True)
        assert len(result) == 0
        _assert_zksynclite_txs_num(cursor, tx_num=0, swap_num=0)

    # re-add a few zksync lite transactions
    with rotki.data.db.user_write() as write_cursor:
        _add_zksynclitetxs(write_cursor)
        _assert_zksynclite_txs_num(write_cursor, tx_num=2, swap_num=1)

    # and check removing only zksync_lite by argument works
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'blockchaintransactionsresource',
        ),
        json={'chain': 'zksync_lite'},
    )
    assert_simple_ok_response(response)
    with rotki.data.db.conn.read_ctx() as cursor:
        _assert_zksynclite_txs_num(cursor, tx_num=0, swap_num=0)

    # check that removing bitcoin events works
    events_db = DBHistoryEvents(rotki.data.db)
    event_identifier1, event_identifier2 = 'xxxx', 'zzzz'
    with rotki.data.db.user_write() as write_cursor:
        for event in [HistoryEvent(
            event_identifier=event_identifier,
            sequence_index=0,
            timestamp=TimestampMS(1600000000000),
            location=Location.BITCOIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_BTC,
            amount=FVal('0.0001'),
        ) for event_identifier in (event_identifier1, event_identifier2)]:
            events_db.add_history_event(
                write_cursor=write_cursor,
                event=event,
                mapping_values=(  # Mark the first event as customized
                    {HISTORY_MAPPING_KEY_STATE: HISTORY_MAPPING_STATE_CUSTOMIZED}
                    if event.event_identifier == event_identifier1 else {}
                ),
            )
        rotki.data.db.set_dynamic_cache(  # also add a cache entry that should get deleted in purge
            write_cursor=write_cursor,
            name=DBCacheDynamic.LAST_BITCOIN_TX_BLOCK,
            value=12345,
            address=BTCAddress('bc1xxxxxxxxxx'),
        )

    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'blockchaintransactionsresource',
        ),
        json={'chain': 'btc'},
    )
    assert_simple_ok_response(response)
    with rotki.data.db.conn.read_ctx() as cursor:
        events = events_db.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(location=Location.BITCOIN),
            has_premium=True,
        )
        assert cursor.execute(
            'SELECT COUNT(*) FROM key_value_cache WHERE name LIKE ?;',
            (f"{DBCacheDynamic.LAST_BITCOIN_TX_BLOCK.value[0].format(address='')}%",),
        ).fetchone()[0] == 0

    # Only the uncustomized event should have been removed.
    assert len(events) == 1
    events[0].event_identifier = event_identifier2


def test_purge_module_data(rotkehlchen_api_server: 'APIServer') -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    def populate_data() -> None:
        with rotki.data.db.user_write() as write_cursor:
            write_cursor.execute(
                'INSERT INTO multisettings(name, value) VALUES(?, ?)',
                ('loopring_0xfoo_account_id', '42'),
            )
            write_cursor.execute(
                'INSERT OR IGNORE INTO eth2_validators(validator_index, '
                'public_key, validator_type, ownership_proportion) VALUES(?, ?, ?, ?)',
                (42, '0xfoo', 1, '1.0'),
            )
            write_cursor.execute(
                'INSERT INTO eth2_daily_staking_details(validator_index, timestamp, pnl) '
                'VALUES(?, ?, ?)',
                (42, 1727172416, '42'),
            )
            write_cursor.execute(
                'INSERT INTO cowswap_orders(identifier, order_type, raw_fee_amount) '
                'VALUES(?, ?, ?)',
                ('foo', 'valid_type', '42'),
            )
            write_cursor.execute(
                'INSERT OR REPLACE INTO key_value_cache(name, value) VALUES(?, ?)',
                (DBCacheStatic.LAST_GNOSISPAY_QUERY_TS.value, '42'),
            )
            write_cursor.execute(
                'INSERT OR REPLACE INTO gnosispay_data(tx_hash, timestamp, merchant_name, '
                'merchant_city, country, mcc, transaction_symbol, transaction_amount, '
                'billing_symbol, billing_amount, reversal_symbol, reversal_amount) '
                'VALUES(?, ?, ?, ?, ? ,?, ?, ?, ?, ?, ?, ?)',
                (make_evm_tx_hash(), 1727172416, 'foo', 'foo', 'ES', 4242, 'EUR', '1', None, None, None, None),  # noqa: E501
            )

    def check_data(name: str | None, before: bool) -> None:
        with rotki.data.db.conn.read_ctx() as cursor:
            if not name or name == 'loopring':
                assert cursor.execute('SELECT COUNT(*) FROM multisettings').fetchone()[0] == (221 if before else 220)  # noqa: E501
            if not name or name == 'eth2':
                assert cursor.execute('SELECT COUNT(*) FROM eth2_daily_staking_details').fetchone()[0] == (1 if before else 0)  # noqa: E501
            if not name or name == 'cowswap':
                assert cursor.execute('SELECT COUNT(*) FROM cowswap_orders').fetchone()[0] == (1 if before else 0)  # noqa: E501
            if not name or name == 'gnosis_pay':
                assert cursor.execute('SELECT COUNT(*) FROM gnosispay_data').fetchone()[0] == (1 if before else 0)  # noqa: E501
                assert cursor.execute('SELECT COUNT(*) FROM key_value_cache').fetchone()[0] == (1 if before else 0)  # noqa: E501

    populate_data()
    check_data(name=None, before=True)
    valid_names = typing.get_args(ModuleName) + typing.get_args(OnlyPurgeableModuleName)
    for name in valid_names:
        response = requests.delete(
            api_url_for(
                rotkehlchen_api_server,
                'namedethereummoduledataresource',
                module_name=name,
            ),
        )
        assert_simple_ok_response(response)
        check_data(name=name, before=False)

    # now recheck that no module name purges all
    populate_data()
    check_data(name=None, before=True)
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'ethereummoduledataresource',
        ),
    )
    assert_simple_ok_response(response)
    check_data(name=None, before=False)


def test_purge_eth2_staking_events_and_cache(rotkehlchen_api_server: 'APIServer') -> None:
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    events_db = DBHistoryEvents(db)
    with db.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=make_eth_withdrawal_and_block_events(),
        )
        for i in range(10):
            db.set_dynamic_cache(
                write_cursor=write_cursor,
                name=DBCacheDynamic.WITHDRAWALS_IDX,
                value=i,
                address=(addy := make_evm_address()),
            )
            db.set_dynamic_cache(
                write_cursor=write_cursor,
                name=DBCacheDynamic.WITHDRAWALS_TS,
                value=make_random_timestamp(),
                address=addy,
            )
            db.set_dynamic_cache(
                write_cursor=write_cursor,
                name=DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS,
                value=make_random_timestamp(),
                index=i,
            )

    for entry_type, cache_keys, expected_event_count in (
            ('eth withdrawal event', ['ethwithdrawalsts%', 'ethwithdrawalsidx%'], 1),
            ('eth block event', ['last_produced_blocks_query_ts%'], 0),
    ):
        response = requests.delete(
            api_url_for(
                rotkehlchen_api_server,
                'eth2stakingeventsresource',
            ), json={'entry_type': entry_type},
        )
        assert_proper_sync_response_with_result(response)
        with db.conn.read_ctx() as cursor:
            assert cursor.execute(
                f'SELECT COUNT(*) FROM key_value_cache WHERE {" OR ".join(["name LIKE ?"] * len(cache_keys))}',  # noqa: E501
                cache_keys,
            ).fetchone()[0] == 0
            assert events_db.get_history_events_count(
                cursor=cursor,
                query_filter=HistoryEventFilterQuery.make(),
            )[0] == expected_event_count
