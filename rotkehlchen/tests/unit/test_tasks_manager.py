from typing import List
from unittest.mock import patch

import gevent
import pytest

from rotkehlchen.chain.bitcoin.hdkey import HDKey
from rotkehlchen.chain.bitcoin.xpub import XpubData
from rotkehlchen.exchanges.manager import ExchangeManager
from rotkehlchen.tasks.manager import TaskManager
from rotkehlchen.utils.misc import ts_now


class MockPremiumSyncManager():

    def __init__(self):
        pass

    def maybe_upload_data_to_server(self) -> None:
        pass


@pytest.fixture(name='max_tasks_num')
def fixture_max_tasks_num() -> int:
    return 5


@pytest.fixture(name='api_task_greenlets')
def fixture_api_task_greenlets() -> List:
    return []


@pytest.fixture(name='exchange_manager')
def fixture_exchange_manager(function_scope_messages_aggregator) -> ExchangeManager:
    return ExchangeManager(msg_aggregator=function_scope_messages_aggregator)


@pytest.fixture(name='task_manager')
def fixture_task_manager(
        database,
        blockchain,
        max_tasks_num,
        greenlet_manager,
        api_task_greenlets,
        cryptocompare,
        exchange_manager,
) -> TaskManager:
    task_manager = TaskManager(
        max_tasks_num=max_tasks_num,
        greenlet_manager=greenlet_manager,
        api_task_greenlets=api_task_greenlets,
        database=database,
        cryptocompare=cryptocompare,
        premium_sync_manager=MockPremiumSyncManager(),  # type: ignore
        chain_manager=blockchain,
        exchange_manager=exchange_manager,
    )
    return task_manager


@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_maybe_query_ethereum_transactions(task_manager, ethereum_accounts):
    task_manager.potential_tasks = [task_manager._maybe_query_ethereum_transactions]
    now = ts_now()

    def tx_query_mock(address, start_ts, end_ts, with_limit):
        assert address in ethereum_accounts
        assert start_ts == 0
        assert end_ts >= now
        assert with_limit is False

    tx_query_patch = patch.object(
        task_manager.chain_manager.ethereum.transactions,
        'single_address_query_transactions',
        wraps=tx_query_mock,
    )

    timeout = 8
    try:
        with gevent.Timeout(timeout):
            with tx_query_patch as tx_mock:
                # First two calls to schedule should handle the addresses
                for i in range(2):
                    task_manager.schedule()
                    while True:
                        if tx_mock.call_count == i + 1:
                            break
                        gevent.sleep(.2)

                task_manager.schedule()
                gevent.sleep(.5)
                assert tx_mock.call_count == 2, '3rd schedule should do nothing'

    except gevent.Timeout as e:
        raise AssertionError(f'The transaction query was not scheduled within {timeout} seconds') from e  # noqa: E501


def test_maybe_schedule_xpub_derivation(task_manager, database):
    xpub = 'xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk'  # noqa: E501
    xpub_data = XpubData(
        xpub=HDKey.from_xpub(xpub=xpub, path='m'),
        derivation_path='m/0/0',
    )
    database.add_bitcoin_xpub(xpub_data)
    task_manager.potential_tasks = [task_manager._maybe_schedule_xpub_derivation]
    xpub_derive_patch = patch(
        'rotkehlchen.chain.bitcoin.xpub.XpubManager.check_for_new_xpub_addresses',
        return_value=None,
    )

    timeout = 4
    try:
        with gevent.Timeout(timeout):
            with xpub_derive_patch as xpub_mock:
                task_manager.schedule()
                while True:
                    if xpub_mock.call_count == 1:
                        break
                    gevent.sleep(.2)

    except gevent.Timeout as e:
        raise AssertionError(f'xpub derivation query was not scheduled within {timeout} seconds') from e  # noqa: E501


def test_maybe_schedule_exchange_query(task_manager, exchange_manager, poloniex):
    now = ts_now()
    task_manager.potential_tasks = [task_manager._maybe_schedule_exchange_history_query]

    def mock_query_history(start_ts, end_ts):
        assert start_ts == 0
        assert end_ts >= now

    exchange_manager.connected_exchanges['poloniex'] = poloniex
    poloniex_patch = patch.object(poloniex, 'query_trade_history', wraps=mock_query_history)

    timeout = 5
    try:
        with gevent.Timeout(timeout):
            with poloniex_patch as poloniex_mock:
                task_manager.schedule()
                while True:
                    if poloniex_mock.call_count == 1:
                        break
                    gevent.sleep(.2)

                task_manager.schedule()
                gevent.sleep(.5)
                assert poloniex_mock.call_count == 1, '2nd schedule should do nothing'

    except gevent.Timeout as e:
        raise AssertionError(f'exchange query was not scheduled within {timeout} seconds') from e  # noqa: E501
