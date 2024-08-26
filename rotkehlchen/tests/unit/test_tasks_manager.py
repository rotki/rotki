import datetime
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock, patch

import gevent
import gevent.lock
import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken, UnderlyingToken
from rotkehlchen.chain.bitcoin.hdkey import HDKey
from rotkehlchen.chain.bitcoin.xpub import XpubData
from rotkehlchen.chain.ethereum.modules.ens.constants import CPT_ENS
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE_V3
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_COMP, A_DAI, A_LUSD, A_USDC, A_USDT, A_YFI
from rotkehlchen.constants.misc import ONE
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.constants.timing import DATA_UPDATES_REFRESH, DAY_IN_SECONDS, WEEK_IN_SECONDS
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.db.calendar import CalendarEntry, CalendarFilterQuery, DBCalendar
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings, ModifiableDBSettings
from rotkehlchen.db.utils import LocationData
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.premium.premium import Premium, PremiumCredentials, SubscriptionStatus
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.tasks.calendar import ENS_CALENDAR_COLOR
from rotkehlchen.tasks.manager import PREMIUM_STATUS_CHECK, TaskManager
from rotkehlchen.tasks.utils import should_run_periodic_task
from rotkehlchen.tests.fixtures.websockets import WebsocketReader
from rotkehlchen.tests.utils.ethereum import (
    TEST_ADDR1,
    TEST_ADDR2,
    get_decoded_events_of_transaction,
    setup_ethereum_transactions_test,
)
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.tests.utils.mock import mock_evm_chains_with_transactions
from rotkehlchen.tests.utils.premium import VALID_PREMIUM_KEY, VALID_PREMIUM_SECRET
from rotkehlchen.types import (
    SPAM_PROTOCOL,
    ChainID,
    EvmTokenKind,
    EVMTxHash,
    Location,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.exchange import ExchangeInterface
    from rotkehlchen.exchanges.manager import ExchangeManager
    from rotkehlchen.rotkehlchen import Rotkehlchen


def test_potential_maybe_schedule_task(task_manager: TaskManager):
    """Check that all the _maybe_... tasks are included in the potential tasks."""
    tasks = {function.__name__ for function in task_manager.potential_tasks}
    assert all(func in tasks for func in dir(task_manager) if func.startswith('_maybe_'))


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('max_tasks_num', [5])
def test_maybe_query_ethereum_transactions(task_manager, ethereum_accounts):
    task_manager.potential_tasks = [task_manager._maybe_query_evm_transactions]
    now = ts_now()

    def tx_query_mock(address, start_ts, end_ts):
        assert address in ethereum_accounts
        assert start_ts == 0
        assert end_ts >= now

    ethereum = task_manager.chains_aggregator.get_chain_manager(SupportedBlockchain.ETHEREUM)
    tx_query_patch = patch.object(
        ethereum.transactions,
        'single_address_query_transactions',
        wraps=tx_query_mock,
    )
    timeout = 8
    try:
        with gevent.Timeout(timeout), tx_query_patch as tx_mock:
            # First two calls to schedule should handle the addresses
            for i in range(2):
                task_manager.schedule()
                while tx_mock.call_count != i + 1:
                    gevent.sleep(.2)

            task_manager.schedule()
            gevent.sleep(.5)
            assert tx_mock.call_count == 2, '3rd schedule should do nothing'

    except gevent.Timeout as e:
        raise AssertionError(f'The transaction query was not scheduled within {timeout} seconds') from e  # noqa: E501


@pytest.mark.parametrize('max_tasks_num', [5])
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
        with gevent.Timeout(timeout), xpub_derive_patch as xpub_mock:
            task_manager.schedule()
            while xpub_mock.call_count != 2:
                gevent.sleep(.2)

    except gevent.Timeout as e:
        raise AssertionError(f'xpub derivation query was not scheduled within {timeout} seconds') from e  # noqa: E501


@pytest.mark.parametrize('max_tasks_num', [5])
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
        with gevent.Timeout(timeout), poloniex_patch as poloniex_mock:
            task_manager.schedule()
            while poloniex_mock.call_count != 1:
                gevent.sleep(.2)

            task_manager.schedule()
            gevent.sleep(.5)
            assert poloniex_mock.call_count == 1, '2nd schedule should do nothing'

    except gevent.Timeout as e:
        raise AssertionError(f'exchange query was not scheduled within {timeout} seconds') from e


def test_maybe_schedule_exchange_query_ignore_exchanges(
        task_manager: 'TaskManager',
        exchange_manager: 'ExchangeManager',
        poloniex: 'ExchangeInterface',
) -> None:
    """Verify that task manager respects the ignored exchanges when querying trades"""
    exchange_manager.connected_exchanges[Location.POLONIEX] = [poloniex]
    task_manager.exchange_manager = exchange_manager
    with task_manager.database.user_write() as cursor:
        task_manager.database.set_settings(cursor, ModifiableDBSettings(
            non_syncing_exchanges=[poloniex.location_id()],
        ))
    assert task_manager._maybe_schedule_exchange_history_query() is None


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('one_receipt_in_db', [True, False])
@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
@pytest.mark.parametrize('max_tasks_num', [5])
def test_maybe_schedule_ethereum_txreceipts(
        task_manager,
        ethereum_manager,
        eth_transactions,
        database,
        one_receipt_in_db,
):
    task_manager.potential_tasks = [task_manager._maybe_schedule_evm_txreceipts]  # pylint: disable=protected-member
    _, receipts = setup_ethereum_transactions_test(
        database=database,
        transaction_already_queried=True,
        one_receipt_in_db=one_receipt_in_db,
    )

    dbevmtx = DBEvmTx(database)
    timeout = 10
    tx_hash_1 = hexstring_to_bytes('0x692f9a6083e905bdeca4f0293f3473d7a287260547f8cbccc38c5cb01591fcda')  # noqa: E501
    tx_hash_2 = hexstring_to_bytes('0x6beab9409a8f3bd11f82081e99e856466a7daf5f04cca173192f79e78ed53a77')  # noqa: E501
    receipt_get_patch = patch.object(ethereum_manager.node_inquirer, 'get_transaction_receipt', wraps=ethereum_manager.node_inquirer.get_transaction_receipt)  # pylint: disable=protected-member  # noqa: E501
    queried_receipts = set()
    try:
        with gevent.Timeout(timeout), receipt_get_patch as receipt_task_mock, mock_evm_chains_with_transactions():  # noqa: E501
            task_manager.schedule()
            with database.conn.read_ctx() as cursor:
                while len(queried_receipts) != 2:
                    for txhash in (tx_hash_1, tx_hash_2):
                        if dbevmtx.get_receipt(cursor, txhash, ChainID.ETHEREUM) is not None:
                            queried_receipts.add(txhash)

                    gevent.sleep(.3)

            task_manager.schedule()
            gevent.sleep(.5)
            assert receipt_task_mock.call_count == 1 if one_receipt_in_db else 2, '2nd schedule should do nothing'  # noqa: E501

    except gevent.Timeout as e:
        raise AssertionError(f'receipts query was not completed within {timeout} seconds') from e

    receipt1 = eth_transactions.get_or_query_transaction_receipt(tx_hash_1)
    assert receipt1 == receipts[0]
    receipt2 = eth_transactions.get_or_query_transaction_receipt(tx_hash_2)
    assert receipt2 == receipts[1]


@pytest.mark.parametrize('max_tasks_num', [7])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_check_premium_status(rotkehlchen_api_server, username):
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
    premium = Premium(credentials=premium_credentials, username=username)
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
                "didn't reactivate the premium status"
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
            assert rotki.premium is not None, "Permium object is None and Periodic check didn't reactivate the premium status"  # noqa: E501


@pytest.mark.parametrize('max_tasks_num', [5])
def test_update_snapshot_balances(rotkehlchen_instance: 'Rotkehlchen'):
    database = rotkehlchen_instance.data.db
    db_history_events = DBHistoryEvents(database)
    with db_history_events.db.conn.read_ctx() as cursor:
        accounts = database.get_blockchain_accounts(cursor).get(SupportedBlockchain.ETHEREUM)

    with db_history_events.db.user_write() as write_cursor:
        database.add_multiple_location_data(
            write_cursor=write_cursor,
            location_data=[LocationData(
                time=Timestamp(2),
                location=Location.ETHEREUM.serialize_for_db(),
                usd_value='',
            )],
        )
        db_history_events.add_history_events(
            write_cursor=write_cursor,
            history=[
                EvmEvent(  # is before last_balance_save
                    event_identifier='0x15ceef8e258c08fc2724c1286da0426cb6ec8df208a9ec269108430c30262791',
                    sequence_index=1,
                    timestamp=TimestampMS(1000),
                    location=Location.OPTIMISM,
                    event_type=HistoryEventType.RECEIVE,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_USDT,
                    balance=Balance(ONE),
                    location_label=accounts[0],
                    tx_hash=make_evm_tx_hash(),
                ), EvmEvent(  # USDT was received before last_balance_save
                    event_identifier='0x25ceef8e258c08fc2724c1286da0426cb6ec8df208a9ec269108430c30262791',
                    sequence_index=1,
                    timestamp=TimestampMS(2000),
                    location=Location.ETHEREUM,
                    event_type=HistoryEventType.WITHDRAWAL,
                    event_subtype=HistoryEventSubType.REMOVE_ASSET,
                    asset=A_USDT,
                    balance=Balance(),
                    location_label=accounts[0],
                    tx_hash=make_evm_tx_hash(),
                ), EvmEvent(  # is a new receive event of this token after last_balance_save
                    event_identifier='0x75ceef8e258c08fc2724c1286da0426cb6ec8df208a9ec269108430c30262791',
                    sequence_index=1,
                    timestamp=TimestampMS(3000),
                    location=Location.ETHEREUM,
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.RECEIVE,
                    asset=A_DAI,
                    balance=Balance(ONE),
                    location_label=accounts[1],
                    tx_hash=make_evm_tx_hash(),
                ), EvmEvent(  # is a new receive event of this token after last_balance_save
                    event_identifier='0x35ceef8e258c08fc2724c1286da0426cb6ec8df208a9ec269108430c30262791',
                    sequence_index=1,
                    timestamp=TimestampMS(4000),
                    location=Location.OPTIMISM,
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.RECEIVE,
                    asset=A_USDC,
                    balance=Balance(ONE),
                    location_label=accounts[2],
                    tx_hash=make_evm_tx_hash(),
                ),
            ],
        )
        # prepopulate the database with tokens
        database.save_tokens_for_address(
            write_cursor=write_cursor,
            address=accounts[1],
            blockchain=SupportedBlockchain.ETHEREUM,
            tokens=[A_COMP, A_LUSD],  # two tokens that we don't have in the events.
        )

    task_manager = rotkehlchen_instance.task_manager
    assert task_manager is not None
    task_manager.potential_tasks = [task_manager._maybe_update_snapshot_balances]
    timeout = 5
    try:
        with (
            gevent.Timeout(timeout),
            patch.object(task_manager, 'query_balances') as query_mock,
            patch.object(
                task_manager.database,
                'save_tokens_for_address',
                side_effect=database.save_tokens_for_address,
            ) as save_tokens_mock,
        ):
            task_manager.schedule()
            while query_mock.call_count != 1:
                gevent.sleep(.2)

            query_mock.assert_called_once_with(
                requested_save_data=True,
                save_despite_errors=False,
                timestamp=None,
                ignore_cache=True,
            )

            assert save_tokens_mock.call_count == 3
            assert save_tokens_mock.call_args_list[0].kwargs['address'] == accounts[1]
            assert save_tokens_mock.call_args_list[0].kwargs['blockchain'] == SupportedBlockchain.ETHEREUM  # noqa: E501
            assert set(save_tokens_mock.call_args_list[0].kwargs['tokens']) == {A_COMP, A_LUSD, A_DAI}  # noqa: E501
            assert save_tokens_mock.call_args_list[1].kwargs['address'] == accounts[2]
            assert save_tokens_mock.call_args_list[1].kwargs['blockchain'] == SupportedBlockchain.OPTIMISM  # noqa: E501
            assert save_tokens_mock.call_args_list[1].kwargs['tokens'] == [A_USDC]
    except gevent.Timeout as e:
        raise AssertionError(f'Update snapshot balances was not completed within {timeout} seconds') from e  # noqa: E501

    # verify that newly saved tokens respects the list of already existing tokens
    with database.conn.read_ctx() as cursor:
        tokens, _ = database.get_tokens_for_address(
            cursor=cursor,
            address=accounts[1],
            blockchain=SupportedBlockchain.ETHEREUM,
        )
        assert set(tokens or {}) == {A_COMP, A_LUSD, A_DAI}


@pytest.mark.parametrize('max_tasks_num', [5])
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
        return [rotki.greenlet_manager.spawn_and_track(
            method=lambda: gevent.sleep(0.1),
            after_seconds=None,
            task_name='Lol kek',
            exception_is_error=True,
        )]

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
        gevent.wait(rotki.task_manager.running_greenlets[simple_task])
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


def test_should_run_periodic_task(database: 'DBHandler') -> None:
    """
    Check that should_run_periodic_task correctly reads the key_value_cache when they have been
    set and where the database doesn't have them yet.
    """
    assert should_run_periodic_task(
        database=database,
        key_name=DBCacheStatic.LAST_DATA_UPDATES_TS,
        refresh_period=DATA_UPDATES_REFRESH,
    ) is True

    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT INTO key_value_cache(name, value) VALUES (?, ?)',
            (DBCacheStatic.LAST_DATA_UPDATES_TS.value, str(ts_now())),
        )

    assert should_run_periodic_task(
        database=database,
        key_name=DBCacheStatic.LAST_DATA_UPDATES_TS,
        refresh_period=DATA_UPDATES_REFRESH,
    ) is False

    # Trigger that the function returns true by having an old timestamp
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'UPDATE key_value_cache SET value=? WHERE NAME=?',
            (str(ts_now() - DATA_UPDATES_REFRESH), DBCacheStatic.LAST_DATA_UPDATES_TS.value),
        )

    assert should_run_periodic_task(
        database=database,
        key_name=DBCacheStatic.LAST_DATA_UPDATES_TS,
        refresh_period=DATA_UPDATES_REFRESH,
    ) is True


@pytest.mark.parametrize('ethereum_accounts', [[make_evm_address()]])
@pytest.mark.parametrize('max_tasks_num', [5])
def test_maybe_kill_running_tx_query_tasks(rotkehlchen_api_server, ethereum_accounts):
    """Test that using maybe_kill_running_tx_query_tasks deletes greenlet from the running tasks

    Also test that if called two times without a schedule() in between, no KeyErrors happen.
    These used to happen before a fix was introduced since the killed greenlet
    was not removed from the tx_query_task_greenlets and/or api_task_greenlets.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    address = ethereum_accounts[0]
    rotki.task_manager.potential_tasks = [rotki.task_manager._maybe_query_evm_transactions]
    eth_manager = rotki.chains_aggregator.get_chain_manager(SupportedBlockchain.ETHEREUM)

    def patched_address_query_transactions(self, address, start_ts, end_ts):  # pylint: disable=unused-argument
        while True:  # busy wait :D just for the test
            gevent.sleep(1)

    query_patch = patch.object(
        eth_manager.transactions,
        'single_address_query_transactions',
        wraps=patched_address_query_transactions,
    )

    with query_patch:
        rotki.task_manager.schedule()  # Schedule the query
        greenlet = rotki.task_manager.running_greenlets[rotki.task_manager._maybe_query_evm_transactions][0]  # noqa: E501
        assert greenlet.dead is False
        assert 'Query ethereum transaction' in greenlet.task_name
        # Running it twice to see it's handled properly and dead greenlet does not raise KeyErrors
        rotki.maybe_kill_running_tx_query_tasks(SupportedBlockchain.ETHEREUM, [address])
        assert greenlet.dead is True
        rotki.maybe_kill_running_tx_query_tasks(SupportedBlockchain.ETHEREUM, [address])
        assert greenlet.dead is True

        # Do a reschedule to see that this clears running greenlets
        rotki.task_manager.potential_tasks = []
        rotki.task_manager.schedule()
        assert len(rotki.task_manager.running_greenlets) == 0


@pytest.mark.parametrize('ethereum_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', '0x9531C059098e3d194fF87FebB587aB07B30B1306']])  # noqa: E501
@pytest.mark.parametrize('ethereum_modules', [['eth2']])
@pytest.mark.parametrize('max_tasks_num', [5])
def test_maybe_query_ethereum_withdrawals(task_manager, ethereum_accounts):
    task_manager.potential_tasks = [task_manager._maybe_query_withdrawals]
    query_patch = patch.object(
        task_manager.chains_aggregator.get_module('eth2'),
        'query_services_for_validator_withdrawals',
        side_effect=lambda *args, **kwargs: None,
    )

    with query_patch as query_mock:
        task_manager.schedule()
        gevent.sleep(0)  # context switch for execution of task
        assert query_mock.call_count == 1

        # test the used query ranges
        for hours_ago, expected_call_count, msg in (
                (5, 2, 'should have ran again'),
                (1, 2, 'should not have ran again'),
        ):
            with task_manager.database.user_write() as write_cursor:
                for address in ethereum_accounts:
                    task_manager.database.set_dynamic_cache(
                        write_cursor=write_cursor,
                        name=DBCacheDynamic.WITHDRAWALS_TS,
                        value=ts_now() - 3600 * hours_ago,
                        address=address,
                    )
            task_manager.schedule()
            gevent.sleep(0)  # context switch for execution of task
            assert query_mock.call_count == expected_call_count, msg


@pytest.mark.parametrize('max_tasks_num', [5])
def test_maybe_detect_new_spam_tokens(
        task_manager: TaskManager,
        database: 'DBHandler',
        globaldb: GlobalDBHandler,
) -> None:
    """Test that the task updating the list of known spam assets works correctly"""
    token = EvmToken.initialize(  # add a token that will be detected as spam
        address=make_evm_address(),
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        name='$ vanityeth.org ($ vanityeth.org)',
        symbol='VANITYTOKEN',
    )
    globaldb.add_asset(asset=token)

    task_manager.potential_tasks = [task_manager._maybe_detect_new_spam_tokens]
    task_manager.schedule()
    gevent.joinall(task_manager.running_greenlets[task_manager._maybe_detect_new_spam_tokens])  # wait for the task to finish since it might context switch while running  # noqa: E501

    updated_token = EvmToken(token.identifier)
    assert updated_token.protocol == SPAM_PROTOCOL
    with database.conn.read_ctx() as cursor:
        assert token.identifier in database.get_ignored_asset_ids(cursor=cursor)
        cursor.execute(
            'SELECT value FROM key_value_cache WHERE name=?',
            (DBCacheStatic.LAST_SPAM_ASSETS_DETECT_KEY.value,),
        )
        assert deserialize_timestamp(cursor.fetchone()[0]) - ts_now() < 2  # saved timestamp should be recent  # noqa: E501


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0xcC3Da35614E6CAEEA7947d7Cd58000C350E7FF84']])
@pytest.mark.parametrize('ethereum_accounts', [['0xb524c787669185E11d01C645D1910631e04Fa5Eb']])
@pytest.mark.parametrize('max_tasks_num', [5])
def test_maybe_augmented_detect_new_spam_tokens(
        task_manager: TaskManager,
        database: 'DBHandler',
        globaldb: GlobalDBHandler,
        gnosis_inquirer,
        ethereum_inquirer,
) -> None:
    """
    Test the augmented spam detection schedule and behaviour. We use a token that is not detected
    in the fast checks that we do and that is airdropped in a multisend transaction.
    """
    tx_hex = deserialize_evm_tx_hash('0x6c10aaafec60e012316f54e2ac691b0a64d8744c21382fd3eb5013b4d1935bab')  # noqa: E501
    get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hex,
    )
    token = EvmToken(evm_address_to_identifier(
        address='0x456FEb37ca5F087f7B59F5F684437cf1dd6e968f',
        chain_id=ChainID.GNOSIS,
        token_type=EvmTokenKind.ERC20,
    ))
    assert token.protocol is None

    # add a transaction for an asset that will get deleted from the
    # globaldb but we will keep the events. To see nothing breaks.
    tx_hex = deserialize_evm_tx_hash('0x5d7e7646e3749fcd575ea76e35763fa8eeb6dfb83c4c242a4448ee1495f695ba')  # noqa: E501
    get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hex,
    )
    globaldb.delete_asset_by_identifier(A_YFI.identifier)

    task_manager.potential_tasks = [task_manager._maybe_augmented_detect_new_spam_tokens]
    task_manager.schedule()
    gevent.joinall(task_manager.running_greenlets[task_manager._maybe_augmented_detect_new_spam_tokens])  # wait for the task to finish since it might context switch while running  # noqa: E501

    updated_token = cast(EvmToken, globaldb.resolve_asset(identifier=token.identifier))
    assert updated_token.protocol == SPAM_PROTOCOL

    with database.conn.read_ctx() as cursor:
        assert token.identifier in database.get_ignored_asset_ids(cursor=cursor)
        cursor.execute(
            'SELECT value FROM key_value_cache WHERE name=?',
            (DBCacheStatic.LAST_AUGMENTED_SPAM_ASSETS_DETECT_KEY.value,),
        )
        assert deserialize_timestamp(cursor.fetchone()[0]) - ts_now() < 2  # saved timestamp should be recent  # noqa: E501


@pytest.mark.parametrize('max_tasks_num', [5])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_tasks_dont_schedule_if_no_eth_address(task_manager: TaskManager) -> None:
    """Test that we don't execute extra logic in tasks if no ethereum address is tracked"""
    with gevent.Timeout(5):  # this should not take long. Otherwise a long running task ran
        task_manager.should_schedule = True
        for func in (
            task_manager._maybe_update_yearn_vaults,
            task_manager._maybe_update_ilk_cache,
        ):
            with (  # if we get to should_update_protocol_cache it means check did not work
                patch('rotkehlchen.chain.ethereum.utils.should_update_protocol_cache') as mocked_func,  # noqa: E501
            ):
                task_manager.potential_tasks = [func]
                task_manager.schedule()
                if len(task_manager.running_greenlets) != 0:
                    gevent.joinall(task_manager.running_greenlets[func])
                assert mocked_func.call_count == 0


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xD4324B81d097141230961af171bC0287F59A2538']])
@pytest.mark.parametrize('max_tasks_num', [5])
def test_augmented_detection_pendle_transactions(
        task_manager: TaskManager,
        globaldb: GlobalDBHandler,
        ethereum_inquirer: 'EthereumInquirer',
) -> None:
    """
    Test that a tx involving transfers about the threshold but from different
    contracts doesn't mark the tokens as spam if the price query fails.
    """
    tx_hex = deserialize_evm_tx_hash('0x9d4ff6ae12790aa747f2f886529092476df6b63e745684b80b8f32c61b90be67')  # noqa: E501
    get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hex,
    )
    token = EvmToken(evm_address_to_identifier(
        address='0x391B570e81e354a85a496952b66ADc831715f54f',
        chain_id=ChainID.ETHEREUM,
        token_type=EvmTokenKind.ERC20,
    ))
    assert token.protocol is None

    task_manager.potential_tasks = [task_manager._maybe_augmented_detect_new_spam_tokens]
    task_manager.schedule()
    with patch(
        'rotkehlchen.externalapis.defillama.Defillama.query_current_price',
        side_effect=lambda *args, **kwargs: (ZERO_PRICE, True),
    ):
        gevent.joinall(task_manager.running_greenlets[task_manager._maybe_augmented_detect_new_spam_tokens])  # wait for the task to finish since it might context switch while running  # noqa: E501

    updated_token = cast(EvmToken, globaldb.resolve_asset(identifier=token.identifier))
    assert updated_token.protocol is None


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('max_tasks_num', [5])
@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
@pytest.mark.parametrize('ethereum_accounts', [[make_evm_address()]])
@pytest.mark.parametrize('optimism_accounts', [[make_evm_address()]])
@pytest.mark.parametrize('base_accounts', [[make_evm_address()]])
@pytest.mark.parametrize('gnosis_accounts', [[make_evm_address()]])
@pytest.mark.parametrize('scroll_accounts', [[make_evm_address()]])
@pytest.mark.parametrize('arbitrum_one_accounts', [[make_evm_address()]])
@pytest.mark.parametrize('polygon_pos_accounts', [[make_evm_address()]])
def test_maybe_update_aave_v3_underlying_assets(
        task_manager: TaskManager,
        globaldb: GlobalDBHandler,
) -> None:
    """Test that the task updating the aave v3 underlying assets in globaldb works"""
    # check the aave v3 underlying assets table in globaldb before running the task
    with globaldb.conn.write_ctx() as write_cursor:
        write_cursor.execute(  # remove all the aave-v3 tokens
            'DELETE FROM assets WHERE identifier IN '
            '(SELECT identifier FROM evm_tokens WHERE protocol = ?);',
            (CPT_AAVE_V3,),
        )

    with globaldb.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM evm_tokens WHERE protocol = ?;', (CPT_AAVE_V3,),
        ).fetchone()[0] == 0

    task_manager.potential_tasks = [task_manager._maybe_update_aave_v3_underlying_assets]
    task_manager.schedule()
    gevent.joinall(task_manager.running_greenlets[task_manager._maybe_update_aave_v3_underlying_assets])  # wait for the task to finish since it might context switch while running  # noqa: E501

    # check the aave v3 underlying assets table in globaldb after running the task
    with globaldb.conn.read_ctx() as write_cursor:
        assert write_cursor.execute(
            'SELECT COUNT(*) FROM evm_tokens WHERE protocol = ?;',
            (CPT_AAVE_V3,),
        ).fetchone()[0] > 0
        assert write_cursor.execute(
            'SELECT COUNT(*) FROM underlying_tokens_list WHERE parent_token_entry IN '
            '(SELECT identifier FROM evm_tokens WHERE protocol = ?);',
            (CPT_AAVE_V3,),
        ).fetchone()[0] > 0

    # test some specific tokens for all the supported chains
    for chain_id, token_address, underlying_token_address in (
        (ChainID.ETHEREUM, '0x102633152313C81cD80419b6EcF66d14Ad68949A', '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),  # noqa: E501
        (ChainID.ETHEREUM, '0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c', '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),  # noqa: E501
        (ChainID.OPTIMISM, '0x38d693cE1dF5AaDF7bC62595A37D667aD57922e5', '0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85'),  # noqa: E501
        (ChainID.OPTIMISM, '0xf329e36C7bF6E5E86ce2150875a84Ce77f477375', '0x76FB31fb4af56892A25e32cFC43De717950c9278'),  # noqa: E501
        (ChainID.POLYGON_POS, '0xA4D94019934D8333Ef880ABFFbF2FDd611C762BD', '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359'),  # noqa: E501
        (ChainID.POLYGON_POS, '0xf329e36C7bF6E5E86ce2150875a84Ce77f477375', '0xD6DF932A45C0f255f85145f286eA0b292B21C90B'),  # noqa: E501
        (ChainID.ARBITRUM_ONE, '0x6533afac2E7BCCB20dca161449A13A32D391fb00', '0x912CE59144191C1204E64559FE8253a0e49E6548'),  # noqa: E501
        (ChainID.ARBITRUM_ONE, '0x38d693cE1dF5AaDF7bC62595A37D667aD57922e5', '0x17FC002b466eEc40DaE837Fc4bE5c67993ddBd6F'),  # noqa: E501
        (ChainID.BASE, '0x4e65fE4DbA92790696d040ac24Aa414708F5c0AB', '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),  # noqa: E501
        (ChainID.BASE, '0x03506214379aA86ad1176af71c260278cfa10B38', '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),  # noqa: E501
        (ChainID.GNOSIS, '0xa818F1B57c201E092C4A2017A91815034326Efd1', '0x6A023CCd1ff6F2045C3309768eAd9E68F978f6e1'),  # noqa: E501
        (ChainID.GNOSIS, '0x23e4E76D01B2002BE436CE8d6044b0aA2f68B68a', '0x6C76971f98945AE98dD7d4DFcA8711ebea946eA6'),  # noqa: E501
        (ChainID.SCROLL, '0x1D738a3436A8C49CefFbaB7fbF04B660fb528CbD', '0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4'),  # noqa: E501
        (ChainID.SCROLL, '0xf301805bE1Df81102C957f6d4Ce29d2B8c056B2a', '0x5300000000000000000000000000000000000004'),  # noqa: E501
    ):
        assert (db_token := globaldb.get_evm_token(
            address=string_to_evm_address(token_address),
            chain_id=chain_id,
        )) is not None
        assert UnderlyingToken(
            address=string_to_evm_address(underlying_token_address),
            token_kind=EvmTokenKind.ERC20,
            weight=ONE,
        ) in db_token.underlying_tokens

    with task_manager.database.conn.read_ctx() as cursor:
        assert task_manager.database.get_static_cache(
            cursor=cursor, name=DBCacheStatic.LAST_AAVE_V3_ASSETS_UPDATE,
        ) is not None

    assert len(task_manager.database.msg_aggregator.rotki_notifier.messages) == 0  # type: ignore[union-attr]  # rotki_notifier is MockRotkiNotifier


@pytest.mark.parametrize('max_tasks_num', [5])
@pytest.mark.freeze_time('2023-04-16 22:31:11 GMT')
@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
def test_send_ws_calendar_reminder(
        rotkehlchen_api_server: 'APIServer',
        websocket_connection: WebsocketReader,
        legacy_messages_via_websockets: bool,  # pylint: disable=unused-argument
        freezer,
) -> None:
    """
    Test that reminders work correctly by:
    - Checking we get the notifications
    - Checking we remove the reminders once fired
    - Checking that starting the app after an event with a reminder passes, triggers the reminder
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    database = rotki.data.db
    task_manager = rotki.task_manager
    assert task_manager is not None

    calendar_db = DBCalendar(database)
    for row in (
        ('Event without reminder', 'event with no reminder', 1713103499),  # 14/04/2024
        ('CRV unlock', 'Unlock date for CRV', 1713621899),  # 20/04/2024
        ('ENS renewal', 'renew yabir.eth', 1714399499),  # 29/04/2024
    ):
        calendar_db.create_calendar_entry(
            calendar=CalendarEntry(
                name=row[0],
                description=row[1],
                timestamp=Timestamp(row[2]),
                counterparty=None,
                address=None,
                blockchain=None,
                color=None,
                auto_delete=False,
            ),
        )
    with database.conn.write_ctx() as write_cursor:
        write_cursor.executemany(
            'INSERT INTO calendar_reminders(event_id, secs_before) VALUES (?, ?)',
            [
                (2, WEEK_IN_SECONDS),  # 13/04/2024
                (3, DAY_IN_SECONDS * 5),  # 24/04/2024
            ],
        )

    task_manager.potential_tasks = [task_manager._maybe_trigger_calendar_reminder]
    task_manager.schedule()
    if len(task_manager.running_greenlets):
        gevent.joinall(task_manager.running_greenlets[task_manager._maybe_trigger_calendar_reminder])  # wait for the task to finish since it might context switch while running  # noqa: E501
    assert websocket_connection.messages_num() == 0

    # move the timestamp to trigger the first event and the event without reminder
    freezer.move_to(datetime.datetime(2024, 4, 19, 20, 0, 1, tzinfo=datetime.UTC))
    task_manager.schedule()
    gevent.joinall(task_manager.running_greenlets[task_manager._maybe_trigger_calendar_reminder])  # wait for the task to finish since it might context switch while running  # noqa: E501
    websocket_connection.wait_until_messages_num(num=1, timeout=2)
    msg = websocket_connection.pop_message()
    assert msg == {
        'data': {
            'identifier': 2,
            'name': 'CRV unlock',
            'description': 'Unlock date for CRV',
            'timestamp': 1713621899,
            'auto_delete': False,
        },
        'type': 'calendar_reminder',
    }

    # check that the reminder got deleted
    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM calendar_reminders WHERE event_id=1',
        ).fetchone()[0] == 0

    # move to the timestamp to trigger the second reminder. Even though we are after
    # the event, we should still get the notification
    freezer.move_to(datetime.datetime(2024, 5, 20, 20, 0, 1, tzinfo=datetime.UTC))
    task_manager.schedule()
    gevent.joinall(task_manager.running_greenlets[task_manager._maybe_trigger_calendar_reminder])  # wait for the task to finish since it might context switch while running  # noqa: E501
    websocket_connection.wait_until_messages_num(num=1, timeout=2)
    msg = websocket_connection.pop_message()
    assert msg == {
        'data': {
            'identifier': 3,
            'name': 'ENS renewal',
            'description': 'renew yabir.eth',
            'timestamp': 1714399499,
            'auto_delete': False,
        },
        'type': 'calendar_reminder',
    }

    # check that the reminder got deleted
    with database.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM calendar_reminders').fetchone()[0] == 0


@pytest.mark.parametrize('max_tasks_num', [5])
@pytest.mark.freeze_time('2023-06-01 22:31:11 GMT')
@pytest.mark.parametrize('db_settings', [
    {'auto_delete_calendar_entries': False},
])
def test_calendar_entries_get_deleted(
        task_manager: TaskManager,
        freezer,
) -> None:
    """
    Test that reminders work correctly by:
    - Checking we get the notifications
    - Checking we remove the reminders once fired
    - Checking that starting the app after an event with a reminder passes, triggers the reminder
    """
    database = task_manager.database
    calendar_db = DBCalendar(database)
    calendar_db.create_calendar_entry(
        calendar=CalendarEntry(
            name='ENS renewal',
            description='renew yabir.eth',
            timestamp=Timestamp(1714399499),
            counterparty=None,
            address=None,
            blockchain=None,
            color=None,
            auto_delete=True,
        ),
    )
    calendar_db.create_calendar_entry(
        calendar=CalendarEntry(
            name='ENS renewal',
            description='renew hania.eth',
            timestamp=Timestamp(1714399499),
            counterparty=None,
            address=None,
            blockchain=None,
            color=None,
            auto_delete=False,
        ),
    )
    with database.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM calendar').fetchone()[0] == 2

    task_manager.potential_tasks = [task_manager._maybe_delete_past_calendar_events]
    task_manager.schedule()
    if len(task_manager.running_greenlets):
        gevent.joinall(task_manager.running_greenlets[task_manager._maybe_delete_past_calendar_events])

    with database.conn.read_ctx() as cursor:  # event should be there because we don't delete due to the setting  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) FROM calendar').fetchone()[0] == 2

    # change the setting and trigger the task again. Move the time to skip the task check
    with database.conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            ('auto_delete_calendar_entries', str(True)),
        )
        CachedSettings().update_entry('auto_delete_calendar_entries', True)
    freezer.move_to(datetime.datetime(2024, 6, 4, 20, 0, 1, tzinfo=datetime.UTC))
    task_manager.schedule()
    gevent.joinall(task_manager.running_greenlets[task_manager._maybe_delete_past_calendar_events])

    with database.conn.read_ctx() as cursor:  # events that are allowed to be deleted shouldn't be there anymore  # noqa: E501
        assert cursor.execute(
            'SELECT description FROM calendar',
        ).fetchall() == [('renew hania.eth',)]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('max_tasks_num', [5])
@pytest.mark.freeze_time('2023-06-01 22:31:11 GMT')
@pytest.mark.parametrize('db_settings', [
    {'auto_create_calendar_reminders': False}, {'auto_create_calendar_reminders': True},
])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
    '0xA3B9E4b2C18eFB1C767542e8eb9419B840881467',
    '0xA01f6D0985389a8E106D3158A9441aC21EAC8D8c',
]])
@pytest.mark.parametrize('ens_data', [(
    [
        deserialize_evm_tx_hash('0x4fdcd2632c6aa5549f884c9322943690e4f3c08e20a4dffe59e198ee737b54e8'),  # Register  # noqa: E501
        deserialize_evm_tx_hash('0xd4fd01f50c3c86e7e119311d6830d975cf7d78d6906004d30370ffcbaabdff95'),  # Renew old (same ENS)  # noqa: E501
    ],
    {'dfern.eth': 2310615949},
), (
    [
        deserialize_evm_tx_hash('0x5150f6e1c76b74fa914e06df9e56577cdeec0faea11f9949ff529daeb16b1c76'),  # Register v2  # noqa: E501
        deserialize_evm_tx_hash('0x0faef1a1a714d5f2f2e5fb344bd186a745180849bae2c92f9d595d8552ef5c96'),  # Renew new  # noqa: E501
    ],
    {'ens2qr.eth': 1712756435, 'karapetsas.eth': 1849443293},
)])
def test_maybe_create_calendar_reminder(
        task_manager: TaskManager,
        ethereum_inquirer: 'EthereumInquirer',
        db_settings: dict[str, Any],
        ens_data: tuple[list['EVMTxHash'], dict[str, Timestamp]],
        add_subgraph_api_key,  # pylint: disable=unused-argument
) -> None:
    """Test that ENS reminders are created at the expiry time of ENS registrations and renewals."""
    ens_tx_hashes, latest_expiry_of_ens = ens_data
    database = task_manager.database
    calendar_db = DBCalendar(database)
    customizable_date = CustomizableDateMixin(database=database)
    all_calendar_entries = calendar_db.query_calendar_entry(CalendarFilterQuery.make())
    assert all_calendar_entries['entries_total'] == 0

    ens_events = [
        next(x for x in get_decoded_events_of_transaction(  # decode ENS registration/renewal event and get the event with the metadata  # noqa: E501
            evm_inquirer=ethereum_inquirer,
            tx_hash=ens_tx_hash,
        )[0] if x.extra_data is not None) for ens_tx_hash in ens_tx_hashes
    ]

    task_manager.potential_tasks = [task_manager._maybe_create_calendar_reminder]
    task_manager.schedule()
    if len(task_manager.running_greenlets):
        gevent.joinall(task_manager.running_greenlets[task_manager._maybe_create_calendar_reminder])

    if db_settings['auto_create_calendar_reminders'] is False:
        assert calendar_db.query_calendar_entry(CalendarFilterQuery.make())['entries_total'] == 0
        return  # finish this test case because this setting will prevent creation of reminders

    new_calendar_entries = calendar_db.query_calendar_entry(CalendarFilterQuery.make())
    assert new_calendar_entries['entries_found'] == len(latest_expiry_of_ens)  # only one calendar entry per ENS  # noqa: E501

    for idx, calendar_entry in enumerate(new_calendar_entries['entries']):
        assert ens_events[idx].extra_data is not None
        assert ens_events[idx].location_label is not None
        ens_name: str = ens_events[idx].extra_data['name']  # type: ignore[index]  # extra_data is not None, checked above
        ens_expires = latest_expiry_of_ens[ens_name]

        assert calendar_entry == CalendarEntry(  # calendar entry is created for expiry
            identifier=idx + 1,
            name=f'{ens_name} expiry',
            timestamp=ens_expires,
            description=f'{ens_name} expires on {customizable_date.timestamp_to_date(ens_expires)}',  # noqa: E501
            counterparty=CPT_ENS,
            address=ens_events[idx].location_label,  # type: ignore[arg-type]  # location_label is not None, checked above
            blockchain=ChainID.deserialize(ens_events[idx].location.to_chain_id()).to_blockchain(),
            color=ENS_CALENDAR_COLOR,
            auto_delete=True,
        )

        # reminders are created 1 week and 1 day before the expiry calendar entry
        reminders = calendar_db.query_reminder_entry(event_id=calendar_entry.identifier)['entries']
        assert len(reminders) == 2
        assert reminders[0].event_id == reminders[1].event_id == calendar_entry.identifier
        assert reminders[0].secs_before == DAY_IN_SECONDS
        assert reminders[1].secs_before == WEEK_IN_SECONDS

    with task_manager.database.conn.read_ctx() as cursor:
        assert (last_ran_ts := task_manager.database.get_static_cache(
            cursor=cursor, name=DBCacheStatic.LAST_CREATE_REMINDER_CHECK_TS,
        )) is not None and last_ran_ts - ts_now() < 5  # executed recently


def test_deadlock_logout(
        rotkehlchen_instance: 'Rotkehlchen',
        globaldb: GlobalDBHandler,  # pylint: disable=unused-argument
):
    """Test that we don't leave locks acquired by a greenlet that has been killed during logout"""
    task_manager = cast(TaskManager, rotkehlchen_instance.task_manager)
    task_manager.max_tasks_num = 10
    task_runs = 0

    def task():
        """Task that will be killed and acquires the lock"""
        nonlocal task_runs
        GlobalDBHandler().packaged_db_lock.acquire()
        while True:
            task_runs += 1
            gevent.sleep(1)

    def maybe_task():
        return [task_manager.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='TEst',
            exception_is_error=True,
            method=task,
        )]

    # schedule the task
    task_manager.should_schedule = True
    task_manager.potential_tasks = [maybe_task]
    task_manager.schedule()

    # ensure that the task runs
    assert task_runs == 0
    gevent.sleep(0)
    assert task_runs == 1

    # logout
    rotkehlchen_instance.logout()

    # context switch to be sure that the task has not been executed again
    gevent.sleep(0)
    assert task_runs == 1

    # shouldn't raise any exception because we released it
    GlobalDBHandler().packaged_db_lock.acquire()
    assert len(task_manager.running_greenlets) == 0


@pytest.mark.parametrize('max_tasks_num', [5])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_snapshots_dont_happen_always(rotkehlchen_api_server: 'APIServer') -> None:
    """Regression test for an issue we had where the task for snapshots was
    creating a snapshot for each run of the background task.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    task_manager = cast(TaskManager, rotki.task_manager)

    task_manager.potential_tasks = [task_manager._maybe_update_snapshot_balances]
    task_manager.should_schedule = True

    query = 'SELECT COUNT(*) FROM timed_location_data'
    with rotki.data.db.conn.read_ctx() as cursor:
        assert cursor.execute(query).fetchone()[0] == 0

        # Schedule the task and check that we got one snapshot.
        task_manager.schedule()
        gevent.joinall(rotki.greenlet_manager.greenlets)
        assert cursor.execute(query).fetchone()[0] == 1

        # Schedule again. The job shouldn't run.
        task_manager.schedule()
        gevent.joinall(rotki.greenlet_manager.greenlets)
        assert cursor.execute(query).fetchone()[0] == 1

        with patch(  # Force a new snapshot.
            'rotkehlchen.db.dbhandler.DBHandler.get_last_balance_save_time',
            return_value=Timestamp(0),
        ):
            task_manager.schedule()
            gevent.joinall(rotki.greenlet_manager.greenlets)

        assert cursor.execute(query).fetchone()[0] == 2
