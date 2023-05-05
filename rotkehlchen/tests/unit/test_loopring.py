from unittest.mock import patch

import pytest

from rotkehlchen.chain.ethereum.modules.l2.loopring import Loopring
from rotkehlchen.constants.assets import A_DPI, A_ETH, A_LRC
from rotkehlchen.db.loopring import DBLoopring
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.mock import MockResponse


@pytest.fixture(name='temp_loopring')
def mock_loopring(function_scope_messages_aggregator, database, ethereum_inquirer):
    return Loopring(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        ethereum_inquirer=ethereum_inquirer,
        premium=None,
    )


def patch_loopring(loopring):
    def mock_requests_get(_url, **kwargs):  # pylint: disable=unused-argument
        response = (
            '[{"tokenId":0,"total":"8427006149700000000","locked":"0",'
            '"pending":{"withdraw":"0","deposit":"0"}},'
            '{"tokenId": 1, "total": "435974889000000000000", "locked": "0",'
            '"pending": {"withdraw": "0", "deposit": "0"}},'
            '{"tokenId":5,"total":"0","locked":"0","pending":{"withdraw":"0","deposit":"0"}},'
            '{"tokenId":70,"total":"2829249920000000000","locked":"0",'
            '"pending":{"withdraw":"0","deposit":"0"}}]'
        )
        return MockResponse(200, response)

    return patch.object(loopring.session, 'get', wraps=mock_requests_get)


def test_loopring_accountid_mapping(database):
    db = DBLoopring(database)
    id1 = 55
    id2 = 67
    addr1 = make_evm_address()
    addr2 = make_evm_address()

    with database.user_write() as cursor:
        assert db.get_accountid_mapping(cursor, addr1) is None
        db.add_accountid_mapping(cursor, addr1, id1)
        assert db.get_accountid_mapping(cursor, addr1) == id1
        db.add_accountid_mapping(cursor, addr2, id2)
        assert db.get_accountid_mapping(cursor, addr2) == id2

        # assure nothing happens with non existing address
        db.remove_accountid_mapping(cursor, make_evm_address())

        db.remove_accountid_mapping(cursor, addr1)
        assert db.get_accountid_mapping(cursor, addr1) is None


def test_get_account_balances(temp_loopring, inquirer):  # pylint: disable=W0613
    """Test the get account balances and check that all the conversions
    are done correctly.
    """
    loopring = temp_loopring
    patched_loopring = patch_loopring(loopring)

    with patched_loopring:
        result = loopring.get_account_balances(account_id=1)
        assert result[A_ETH].amount == FVal(8.4270061497)
        assert result[A_LRC].amount == FVal(435.974889)
        assert result[A_DPI].amount == FVal(2.82924992)


def test_get_balances(temp_loopring, inquirer):  # pylint: disable=W0613
    """Test that loopring's get_balances can be called"""
    loopring = temp_loopring
    patched_loopring = patch_loopring(loopring)

    with patched_loopring:
        loopring.get_balances(addresses=[])
