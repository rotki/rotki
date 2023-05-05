from random import randint, uniform

import gevent
import pytest

from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.filtering import LedgerActionsFilterQuery
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.fval import FVal
from rotkehlchen.types import Location


def make_ledger_action():
    return LedgerAction(
        identifier=1,
        timestamp=randint(1, 16433333),
        asset=A_ETH,
        action_type=LedgerActionType.INCOME,
        location=Location.BLOCKCHAIN,
        amount=FVal(randint(1, 1642323)),
        rate=FVal(uniform(0.00001, 5)),
        link='dasd',
        notes='asdsad',
    )


def write_actions(database, num):
    actions = [make_ledger_action() for _ in range(1, num)]
    query = """
    INSERT INTO ledger_actions(
    timestamp, type, location, amount, asset, rate, rate_asset, link, notes
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);"""
    with database.user_write() as cursor:
        cursor.executemany(query, [x.serialize_for_db() for x in actions])


def write_single_action(database, action):
    query = """
    INSERT INTO ledger_actions(
    timestamp, type, location, amount, asset, rate, rate_asset, link, notes
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);"""
    with database.user_write() as write_cursor:
        write_cursor.execute(query, action.serialize_for_db())


def write_single_action_frequently(database, num, sleep_between_writes):
    for _ in range(num):
        write_single_action(database, make_ledger_action())
        gevent.sleep(sleep_between_writes)


def read_single_action_frequently(database, msg_aggregator, num, limit, sleep_between_reads):
    dbla = DBLedgerActions(database, msg_aggregator)
    for _ in range(num):
        with database.conn.read_ctx() as cursor:
            dbla.get_ledger_actions(cursor, LedgerActionsFilterQuery.make(limit=limit), has_premium=True)  # noqa: E501
        gevent.sleep(sleep_between_reads)


def read_actions(database, limit, msg_aggregator):
    dbla = DBLedgerActions(database, msg_aggregator)
    with database.conn.read_ctx() as cursor:
        dbla.get_ledger_actions(
            cursor,
            LedgerActionsFilterQuery.make(limit=limit),
            has_premium=True,
        )


@pytest.mark.parametrize('sql_vm_instructions_cb', [100])
def test_callback_segfault_simple(database, function_scope_messages_aggregator):
    """Test that the async and sqlite progress handler segfault yielding bug does not hit us
    This one is protected against by having the lock inside the callback.

    The bug can be summed up as following:
    1. Get in the progress callback
    2. Context switch out of the callback with sleep(0)
    3. Enter critical section, which essentially disables the callback
    4. Write/read more data in the DB
    5. Exit critical section, re-enabling the callback
    6. Context switch back to the progress callback of (1) and exit it.
    7. Segmentation fault.
    """
    # first write some data in the DB to have enough data to read.
    write_actions(database, 1000)

    # Then start reading from one greenlet and writing from others to create the problem
    a = gevent.spawn(
        read_actions,
        database=database,
        limit=100,
        msg_aggregator=function_scope_messages_aggregator,
    )
    b = gevent.spawn(write_actions, database=database, num=200)
    c = gevent.spawn(write_actions, database=database, num=200)
    gevent.joinall([a, b, c])


@pytest.mark.parametrize('sql_vm_instructions_cb', [100])
def test_callback_segfault_complex(database, function_scope_messages_aggregator):
    """Test that we protect against the yielding segfault bug that happens when lots
    of complicated actions happen at the same time.

    The bug can be summed up as following:
    1. Get in the progress callback but before the in_callback lock is acquired.
    2. Wait for the lock acquisition and context switch out
    3.A lot of things happen and the callback gets entered by a lot of other sections
    and has the lock acquired. Some of those places do connection.commit
    and modify the connection. As per the docs that's a no no.
    https://www.sqlite.org/c3ref/progress_handler.html
    4. We context switch back to the original callback acquire the lock and then release it
    and the callback is exited. Since the connection has been modified KABOOM SEGFAULT.
    """
    # first write some data in the DB to have enough data to read.
    write_actions(database, 500)

    # Then have lots of stuff happen at the same time so that the situation described
    # in the docstring occurs
    a = gevent.spawn(
        read_actions,
        database=database,
        limit=50,
        msg_aggregator=function_scope_messages_aggregator,
    )
    b = gevent.spawn(
        write_actions,
        database=database,
        num=100,
    )
    c = gevent.spawn(
        write_single_action_frequently,
        database=database,
        num=10,
        sleep_between_writes=0.5,
    )
    d = gevent.spawn(
        read_single_action_frequently,
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        num=10,
        limit=1,
        sleep_between_reads=0.5,
    )
    e = gevent.spawn(
        write_actions,
        database=database,
        num=100,
    )
    gevent.joinall([a, b, c, d, e])


@pytest.mark.parametrize('sql_vm_instructions_cb', [0])
def test_can_disable_callback(database):  # pylint: disable=unused-argument
    """Simply test that setting sql_vm_instructions_cb to 0 works

    This is a regression test since setting to 0 was hitting an assertion before
    """
    assert True  # no need to do anything. Test would fail at fixture setup
