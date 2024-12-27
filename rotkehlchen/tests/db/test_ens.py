import datetime

import pytest
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.db.ens import DBEns
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import ChecksumEvmAddress, EnsMapping, Timestamp
from rotkehlchen.utils.misc import ts_now

START_TS = Timestamp(1279940400)


def _simple_ens_setup(database, freezer) -> tuple[DBEns, ChecksumEvmAddress, ChecksumEvmAddress]:
    dbens = DBEns(database)
    freezer.move_to(datetime.datetime.fromtimestamp(START_TS, tz=datetime.UTC))
    addy1 = make_evm_address()
    addy2 = make_evm_address()
    with database.user_write() as write_cursor:
        dbens.add_ens_mapping(write_cursor, addy1, 'addy1', ts_now())
        dbens.add_ens_mapping(write_cursor, addy2, 'addy2', ts_now())

    with database.conn.read_ctx() as cursor:
        mappings = dbens.get_reverse_ens(cursor, [addy1, addy2])
    assert mappings == {
        addy1: EnsMapping(
            address=addy1,
            name='addy1',
            last_update=START_TS,
        ),
        addy2: EnsMapping(
            address=addy2,
            name='addy2',
            last_update=START_TS,
        ),
    }

    return dbens, addy1, addy2


@pytest.mark.freeze_time
def test_simple_ens_mapping(database, freezer):
    _simple_ens_setup(database, freezer)


def test_empty_addresses(database):
    dbens = DBEns(db_handler=database)
    with database.conn.read_ctx() as cursor:
        res = dbens.get_reverse_ens(cursor, addresses=[])
    assert res == {}


@pytest.mark.freeze_time
def test_update_ens_mapping(database, freezer):
    dbens, addy1, addy2 = _simple_ens_setup(database, freezer)

    ts2 = START_TS + 3600
    freezer.move_to(datetime.datetime.fromtimestamp(ts2, tz=datetime.UTC))
    with database.user_write() as write_cursor:
        dbens.add_ens_mapping(write_cursor, addy1, None, ts_now())

    with database.conn.read_ctx() as cursor:
        mappings = dbens.get_reverse_ens(cursor, [addy1, addy2])
        assert mappings == {
            addy1: ts2,
            addy2: EnsMapping(
                address=addy2,
                name='addy2',
                last_update=START_TS,
            ),
        }

        ts3 = ts2 + 3600
        freezer.move_to(datetime.datetime.fromtimestamp(ts3, tz=datetime.UTC))
        with database.user_write() as write_cursor:
            dbens.add_ens_mapping(write_cursor, addy1, 'new addy1 name', ts_now())

        mappings = dbens.get_reverse_ens(cursor, [addy1, addy2])
        assert mappings == {
            addy1: EnsMapping(
                address=addy1,
                name='new addy1 name',
                last_update=ts3,
            ),
            addy2: EnsMapping(
                address=addy2,
                name='addy2',
                last_update=START_TS,
            ),
        }

        ts4 = ts3 + 3600
        freezer.move_to(datetime.datetime.fromtimestamp(ts4, tz=datetime.UTC))
        with database.user_write() as write_cursor:
            dbens.add_ens_mapping(write_cursor, addy2, 'new addy2 name', ts_now())

        mappings = dbens.get_reverse_ens(cursor, [addy1, addy2])

    assert mappings == {
        addy1: EnsMapping(
            address=addy1,
            name='new addy1 name',
            last_update=ts3,
        ),
        addy2: EnsMapping(
            address=addy2,
            name='new addy2 name',
            last_update=ts4,
        ),
    }


@pytest.mark.freeze_time
def test_multiple_ens_mapping_none(database, freezer):
    dbens, addy1, addy2 = _simple_ens_setup(database, freezer)

    # set one to None
    ts2 = START_TS + 3600
    freezer.move_to(datetime.datetime.fromtimestamp(ts2, tz=datetime.UTC))
    with database.user_write() as write_cursor:
        dbens.add_ens_mapping(write_cursor, addy1, None, ts_now())

    with database.conn.read_ctx() as cursor:
        mappings = dbens.get_reverse_ens(cursor, [addy1, addy2])
        assert mappings == {
            addy1: ts2,
            addy2: EnsMapping(
                address=addy2,
                name='addy2',
                last_update=START_TS,
            ),
        }

        # set another to None at the same time
        ts3 = START_TS + 3600
        freezer.move_to(datetime.datetime.fromtimestamp(ts3, tz=datetime.UTC))
        with database.user_write() as write_cursor:
            dbens.add_ens_mapping(write_cursor, addy2, None, ts_now())
        mappings = dbens.get_reverse_ens(cursor, [addy1, addy2])

    assert mappings == {
        addy1: ts2,
        addy2: ts3,
    }


@pytest.mark.freeze_time
def test_conflict(database, freezer):
    dbens, addy1, addy2 = _simple_ens_setup(database, freezer)
    addy3 = make_evm_address()
    with database.user_write() as write_cursor:
        dbens.add_ens_mapping(write_cursor, addy1, 'addy1', ts_now())  # adding existing mapping == noop  # noqa: E501

        # Check that simply adding existing name for other address raises
        ts2 = START_TS + 3600
        freezer.move_to(datetime.datetime.fromtimestamp(ts2, tz=datetime.UTC))
        with pytest.raises(sqlcipher.IntegrityError):  # pylint: disable=no-member
            dbens.add_ens_mapping(write_cursor, addy3, 'addy1', ts_now())

    with database.conn.read_ctx() as cursor:
        mappings = dbens.get_reverse_ens(cursor, [addy1, addy2, addy3])

        assert mappings == {
            addy1: EnsMapping(
                address=addy1,
                name='addy1',
                last_update=START_TS,
            ),
            addy2: EnsMapping(
                address=addy2,
                name='addy2',
                last_update=START_TS,
            ),
        }

        # Use the update values function to do it properly
        mappings_to_send = dbens.update_values(
            write_cursor=cursor,
            ens_lookup_results={addy3: 'addy1'},
            mappings_to_send={},
        )
        assert mappings_to_send == {addy3: 'addy1'}
        # confirm addy3 replaced addy1
        mappings = dbens.get_reverse_ens(cursor, [addy1, addy2, addy3])

    assert mappings == {
        addy3: EnsMapping(
            address=addy3,
            name='addy1',
            last_update=ts2,
        ),
        addy2: EnsMapping(
            address=addy2,
            name='addy2',
            last_update=START_TS,
        ),
    }
