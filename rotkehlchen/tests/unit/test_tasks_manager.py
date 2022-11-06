from typing import List
from unittest.mock import MagicMock, patch

import gevent
import pytest

from rotkehlchen.chain.bitcoin.hdkey import HDKey
from rotkehlchen.chain.bitcoin.xpub import XpubData
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.premium.premium import Premium, PremiumCredentials, SubscriptionStatus
from rotkehlchen.tasks.manager import PREMIUM_STATUS_CHECK, TaskManager
from rotkehlchen.tests.utils.ethereum import setup_ethereum_transactions_test
from rotkehlchen.tests.utils.premium import VALID_PREMIUM_KEY, VALID_PREMIUM_SECRET
from rotkehlchen.types import Location, SupportedBlockchain
from rotkehlchen.utils.hexbytes import hexstring_to_bytes
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


@pytest.fixture(name='task_manager')
def fixture_task_manager(
        database,
        blockchain,
        max_tasks_num,
        greenlet_manager,
        api_task_greenlets,
        cryptocompare,
        exchange_manager,
        evm_transaction_decoder,
        messages_aggregator,
) -> TaskManager:
    task_manager = TaskManager(
        max_tasks_num=max_tasks_num,
        greenlet_manager=greenlet_manager,
        api_task_greenlets=api_task_greenlets,
        database=database,
        cryptocompare=cryptocompare,
        premium_sync_manager=MockPremiumSyncManager(),  # type: ignore
        chains_aggregator=blockchain,
        exchange_manager=exchange_manager,
        eth_tx_decoder=evm_transaction_decoder,
        deactivate_premium=lambda: None,
        query_balances=lambda: None,
        update_curve_pools_cache=lambda: None,
        activate_premium=lambda _: None,
        msg_aggregator=messages_aggregator,
    )
    return task_manager


@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_maybe_query_ethereum_transactions(task_manager, ethereum_accounts):
    task_manager.potential_tasks = [task_manager._maybe_query_ethereum_transactions]
    now = ts_now()

    def tx_query_mock(address, start_ts, end_ts):
        assert address in ethereum_accounts
        assert start_ts == 0
        assert end_ts >= now

    tx_query_patch = patch.object(
        task_manager.eth_tx_decoder.transactions,
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
    xpub_data1 = XpubData(
        xpub=HDKey.from_xpub(xpub=xpub, path='m'),
        blockchain=SupportedBlockchain.BITCOIN,
        derivation_path='m/0/0',
    )
    xpub_data2 = XpubData(
        xpub=HDKey.from_xpub(xpub=xpub, path='m'),
        blockchain=SupportedBlockchain.BITCOIN_CASH,
        derivation_path='m/0/0',
    )
    with database.user_write() as cursor:
        database.add_bitcoin_xpub(cursor, xpub_data1)
        database.add_bitcoin_xpub(cursor, xpub_data2)

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
                    if xpub_mock.call_count == 2:
                        break
                    gevent.sleep(.2)

    except gevent.Timeout as e:
        raise AssertionError(f'xpub derivation query was not scheduled within {timeout} seconds') from e  # noqa: E501


def test_maybe_schedule_exchange_query(task_manager, exchange_manager, poloniex):
    now = ts_now()
    task_manager.potential_tasks = [task_manager._maybe_schedule_exchange_history_query]

    def mock_query_history(start_ts, end_ts, only_cache):
        assert start_ts == 0
        assert end_ts >= now
        assert only_cache is False

    exchange_manager.connected_exchanges[Location.POLONIEX] = [poloniex]
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


@pytest.mark.parametrize('one_receipt_in_db', [True, False])
def test_maybe_schedule_ethereum_txreceipts(
        task_manager,
        ethereum_manager,
        eth_transactions,
        database,
        one_receipt_in_db,
):
    task_manager.potential_tasks = [task_manager._maybe_schedule_ethereum_txreceipts]  # pylint: disable=protected-member  # noqa: E501
    _, receipts = setup_ethereum_transactions_test(
        database=database,
        transaction_already_queried=True,
        one_receipt_in_db=one_receipt_in_db,
    )

    dbethtx = DBEthTx(database)
    timeout = 10
    tx_hash_1 = hexstring_to_bytes('0x692f9a6083e905bdeca4f0293f3473d7a287260547f8cbccc38c5cb01591fcda')  # noqa: E501
    tx_hash_2 = hexstring_to_bytes('0x6beab9409a8f3bd11f82081e99e856466a7daf5f04cca173192f79e78ed53a77')  # noqa: E501
    receipt_get_patch = patch.object(ethereum_manager, 'get_transaction_receipt', wraps=ethereum_manager.get_transaction_receipt)  # pylint: disable=protected-member  # noqa: E501
    queried_receipts = set()
    try:
        with gevent.Timeout(timeout):
            with receipt_get_patch as receipt_task_mock:
                task_manager.schedule()
                with database.conn.read_ctx() as cursor:
                    while True:
                        if len(queried_receipts) == 2:
                            break

                        for txhash in (tx_hash_1, tx_hash_2):
                            if dbethtx.get_receipt(cursor, txhash) is not None:
                                queried_receipts.add(txhash)

                        gevent.sleep(.3)

                task_manager.schedule()
                gevent.sleep(.5)
                assert receipt_task_mock.call_count == 1 if one_receipt_in_db else 2, '2nd schedule should do nothing'  # noqa: E501

    except gevent.Timeout as e:
        raise AssertionError(f'receipts query was not completed within {timeout} seconds') from e  # noqa: E501

    with database.user_write() as cursor:
        receipt1 = eth_transactions.get_or_query_transaction_receipt(cursor, tx_hash_1)
        assert receipt1 == receipts[0]
        receipt2 = eth_transactions.get_or_query_transaction_receipt(cursor, tx_hash_2)
        assert receipt2 == receipts[1]


@pytest.mark.parametrize('max_tasks_num', [7])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_check_premium_status(rotkehlchen_api_server):
    """
    Test that the premium check tasks works correctly. The tests creates a valid subscription
    and verifies that after the task was scheduled the users premium is deactivated.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    gevent.killall(rotki.api_task_greenlets)
    task_manager = rotki.task_manager
    task_manager.potential_tasks = [task_manager._maybe_check_premium_status]
    task_manager.last_premium_status_check = ts_now() - 3601

    premium_credentials = PremiumCredentials(VALID_PREMIUM_KEY, VALID_PREMIUM_SECRET)
    premium = Premium(premium_credentials)
    premium.status = SubscriptionStatus.ACTIVE

    def mock_check_premium_status():
        task_manager.last_premium_status_check = ts_now() - PREMIUM_STATUS_CHECK
        task_manager._maybe_check_premium_status()

    with patch(
        'rotkehlchen.db.dbhandler.DBHandler.get_rotkehlchen_premium',
        MagicMock(return_value=premium_credentials),
    ):
        assert premium.is_active() is True
        assert rotki.premium is not None

        with patch('rotkehlchen.premium.premium.Premium.is_active', MagicMock(return_value=False)):
            mock_check_premium_status()
            assert rotki.premium is None, (
                'Premium object is not None and should be'
                'deactivated after invalid premium credentials'
            )

        with patch('rotkehlchen.premium.premium.Premium.is_active', MagicMock(return_value=True)):
            mock_check_premium_status()
            assert rotki.premium is not None, (
                'Permium object is None and Periodic check'
                'didn\'t reactivate the premium status'
            )

        with patch(
            'rotkehlchen.premium.premium.Premium.is_active',
            MagicMock(side_effect=RemoteError()),
        ):
            for check_trial in range(3):
                mock_check_premium_status()
                assert rotki.premium is not None, f'Premium object is None and should be active after the {check_trial} periodic check'  # noqa: E501

            mock_check_premium_status()
            assert rotki.premium is None, 'Premium object is not None and should be deactivated after the 4th periodic check'  # noqa: E501

        with patch('rotkehlchen.premium.premium.Premium.is_active', MagicMock(return_value=True)):
            mock_check_premium_status()
            assert rotki.premium is not None, 'Permium object is None and Periodic check didn\'t reactivate the premium status'  # noqa: E501


def test_update_snapshot_balances(task_manager):
    task_manager.potential_tasks = [task_manager._maybe_update_snapshot_balances]
    query_balances_patch = patch.object(
        task_manager,
        'query_balances',
    )
    timeout = 5
    try:
        with gevent.Timeout(timeout):
            with query_balances_patch as query_mock:
                task_manager.schedule()
                while True:
                    if query_mock.call_count == 1:
                        break
                    gevent.sleep(.2)

                query_mock.assert_called_once_with(
                    requested_save_data=True,
                    save_despite_errors=False,
                    timestamp=None,
                    ignore_cache=True,
                )
    except gevent.Timeout as e:
        raise AssertionError(f'Update snapshot balances was not completed within {timeout} seconds') from e  # noqa: E501


def test_update_curve_pools(task_manager):
    """Check that task for curve pools cache update is scheduled properly."""
    task_manager.potential_tasks = [task_manager._maybe_update_curve_pools]
    query_balances_patch = patch.object(
        task_manager,
        'update_curve_pools_cache',
    )
    timeout = 5
    try:
        with gevent.Timeout(timeout):
            with query_balances_patch as query_mock:
                task_manager.schedule()
                while True:
                    if query_mock.call_count == 1:
                        break
                    gevent.sleep(.2)
    except gevent.Timeout as e:
        raise AssertionError(f'Update curve pools was not completed within {timeout} seconds') from e  # noqa: E501


def test_try_start_same_task(rotkehlchen_api_server):
    """
    1. Checks that it is not possible to start 2 same tasks
    2. Checks that is possible to start second same task when the first one finishes
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    # Using rotki.greenlet_manager instead of pure GreenletManager() since patch.object
    # needs it for proper mocking
    spawn_patch = patch.object(
        rotki.greenlet_manager,
        'spawn_and_track',
        wraps=rotki.greenlet_manager.spawn_and_track,
    )

    def simple_task():
        return rotki.greenlet_manager.spawn_and_track(
            method=lambda: gevent.sleep(0.1),
            after_seconds=None,
            task_name='Lol kek',
            exception_is_error=True,
        )

    with spawn_patch as patched:
        rotki.task_manager.potential_tasks = [rotki.task_manager._maybe_update_snapshot_balances]
        rotki.task_manager.schedule()
        rotki.task_manager.schedule()
        assert patched.call_count == 1
        # Check that mapping in the task manager is correct
        assert rotki.task_manager.running_greenlets.keys() == {
            rotki.task_manager._maybe_update_snapshot_balances,
        }
        rotki.task_manager.potential_tasks = [simple_task]
        rotki.task_manager.schedule()  # start a small greenlet
        assert patched.call_count == 2
        assert rotki.task_manager.running_greenlets.keys() == {
            rotki.task_manager._maybe_update_snapshot_balances,
            simple_task,  # check that mapping was updated
        }
        # Wait until our small greenlet finishes
        gevent.wait([rotki.task_manager.running_greenlets[simple_task]])
        rotki.task_manager.potential_tasks = []
        rotki.task_manager.schedule()  # clear the mapping
        assert rotki.task_manager.running_greenlets.keys() == {  # and check that it was removed
            rotki.task_manager._maybe_update_snapshot_balances,
        }
        # And make sure that now we are able to start it again
        rotki.task_manager.potential_tasks = [simple_task]
        rotki.task_manager.schedule()
        assert patched.call_count == 3
        assert rotki.task_manager.running_greenlets.keys() == {
            rotki.task_manager._maybe_update_snapshot_balances,
            simple_task,
        }
