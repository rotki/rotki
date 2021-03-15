from unittest.mock import patch

import pytest

from rotkehlchen.db.loopring import DBLoopring
from rotkehlchen.chain.ethereum.modules.l2.loopring import Loopring
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.tests.utils.mock import MockResponse


@pytest.fixture(scope='function', name='temp_loopring')
def fixture_temp_loopring(function_scope_messages_aggregator, database, ethereum_manager):
    return Loopring(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        ethereum_manager=ethereum_manager,
        premium=None,
    )


def patch_loopring(loopring):
    def mock_requests_get(_url):
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
    addr1 = make_ethereum_address()
    addr2 = make_ethereum_address()

    assert db.get_accountid_mapping(addr1) is None
    db.add_accountid_mapping(addr1, id1)
    assert db.get_accountid_mapping(addr1) == id1
    db.add_accountid_mapping(addr2, id2)
    assert db.get_accountid_mapping(addr2) == id2

    # assure nothing happens with non existing address
    db.remove_accountid_mapping(make_ethereum_address())

    db.remove_accountid_mapping(addr1)
    assert db.get_accountid_mapping(addr1) is None


def test_query_balances(temp_loopring, inquirer):  # pylint: disable=W0613
    """Test the get account balances and check that all the conversions
    are done correctly.
    """
    loopring = temp_loopring
    patched_loopring = patch_loopring(loopring)

    with patched_loopring:
        result = loopring.get_account_balances(1)
        assert result['ETH'].amount == FVal(8.4270061497)
        assert result['LRC'].amount == FVal(435.974889)
        assert result['DPI'].amount == FVal(2.82924992)
