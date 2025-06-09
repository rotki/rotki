from random import randint
from uuid import uuid4

import pytest

from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import Location, TimestampMS
from rotkehlchen.utils.concurrency import timeout as Timeout, joinall, sleep, spawn


def make_history_event():
    return HistoryEvent(
        event_identifier=uuid4().hex,
        sequence_index=0,
        timestamp=TimestampMS(randint(1000, 16433333000)),
        location=Location.BLOCKCHAIN,
        asset=A_ETH,
        amount=FVal(randint(1, 1642323)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        notes='asdsad',
    )


def write_events(database, num):
    dbevents = DBHistoryEvents(database)
    events = [make_history_event() for _ in range(1, num)]
    with database.user_write() as write_cursor:
        dbevents.add_history_events(write_cursor=write_cursor, history=events)


def write_single_event(database, event):
    dbevents = DBHistoryEvents(database)
    with database.user_write() as write_cursor:
        dbevents.add_history_event(write_cursor, event)


def write_single_event_frequently(database, num, sleep_between_writes):
    for _ in range(num):
        write_single_event(database, make_history_event())
        sleep(sleep_between_writes)


def read_single_event_frequently(database, num, limit, sleep_between_reads):
    dbevents = DBHistoryEvents(database)
    for _ in range(num):
        with database.conn.read_ctx() as cursor:
            dbevents.get_history_events(cursor, HistoryEventFilterQuery.make(limit=limit), has_premium=True)  # noqa: E501
        sleep(sleep_between_reads)


def read_events(database, limit):
    dbevents = DBHistoryEvents(database)
    with database.conn.read_ctx() as cursor:
        dbevents.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(limit=limit),
            has_premium=True,
        )


@pytest.mark.parametrize('sql_vm_instructions_cb', [100])
def test_callback_segfault_simple(database):
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
    write_events(database, 1000)

    # Then start reading from one greenlet and writing from others to create the problem
    a = spawn(
        read_events,
        database=database,
        limit=100,
    )
    b = spawn(write_events, database=database, num=200)
    c = spawn(write_events, database=database, num=200)
    joinall([a, b, c])


@pytest.mark.parametrize('sql_vm_instructions_cb', [100])
def test_callback_segfault_complex(database):
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
    write_events(database, 500)

    # Then have lots of stuff happen at the same time so that the situation described
    # in the docstring occurs
    a = spawn(
        read_events,
        database=database,
        limit=50,
    )
    b = spawn(
        write_events,
        database=database,
        num=100,
    )
    c = spawn(
        write_single_event_frequently,
        database=database,
        num=10,
        sleep_between_writes=0.5,
    )
    d = spawn(
        read_single_event_frequently,
        database=database,
        num=10,
        limit=1,
        sleep_between_reads=0.5,
    )
    e = spawn(
        write_events,
        database=database,
        num=100,
    )
    joinall([a, b, c, d, e])


@pytest.mark.parametrize('sql_vm_instructions_cb', [0])
def test_can_disable_callback(database):  # pylint: disable=unused-argument
    """Simply test that setting sql_vm_instructions_cb to 0 works

    This is a regression test since setting to 0 was hitting an assertion before
    """
    assert True  # no need to do anything. Test would fail at fixture setup
