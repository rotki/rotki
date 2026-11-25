from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.errors.misc import APIKeyNotAvailable, RemoteError
from rotkehlchen.externalapis.opensea import Opensea
from rotkehlchen.tests.fixtures.messages import MockRotkiNotifier
from rotkehlchen.tests.utils.mock import MockResponse

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler

ACCOUNT_OPTIONS = {'address': '0x9531C059098e3d194fF87FebB587aB07B30B1306'}


@pytest.fixture(name='opensea')
def fixture_opensea(database: DBHandler, ethereum_inquirer: EthereumInquirer) -> Opensea:
    database.msg_aggregator.rotki_notifier = MockRotkiNotifier()  # type: ignore[assignment]
    return Opensea(
        database=database,
        msg_aggregator=database.msg_aggregator,
        ethereum_inquirer=ethereum_inquirer,
    )


@pytest.mark.parametrize('include_opensea_key', [False])
def test_no_query_without_api_key(opensea: Opensea) -> None:
    """OpenSea rejects keyless queries, so without a key rotki makes none, instead of retrying
    with backoff for half a minute."""
    with (
        patch.object(opensea.session, 'get') as get_mock,
        pytest.raises(APIKeyNotAvailable, match='An OpenSea API key is needed'),
    ):
        opensea._query(endpoint='assets', options=ACCOUNT_OPTIONS)

    assert get_mock.call_count == 0
    assert opensea.db.msg_aggregator.rotki_notifier.pop_message() is None  # type: ignore[union-attr]


def test_rejected_api_key_fails_without_retrying(opensea: Opensea) -> None:
    """A rejected key does not get accepted by waiting, so it fails at once."""
    with (
        patch.object(opensea.session, 'get', return_value=MockResponse(HTTPStatus.UNAUTHORIZED, '{}')) as get_mock,  # noqa: E501
        patch('rotkehlchen.externalapis.opensea.cancellable_sleep') as sleep_mock,
        pytest.raises(RemoteError, match='rejected the API key'),
    ):
        opensea._query(endpoint='assets', options=ACCOUNT_OPTIONS)

    assert get_mock.call_count == 1
    assert sleep_mock.call_count == 0
    assert opensea.db.msg_aggregator.rotki_notifier.pop_message() is None  # type: ignore[union-attr]


@pytest.mark.parametrize('status_code', [HTTPStatus.TOO_MANY_REQUESTS, HTTPStatus.BAD_GATEWAY])
def test_rate_limit_and_server_errors_are_retried(opensea: Opensea, status_code: HTTPStatus) -> None:  # noqa: E501
    with (
        patch.object(opensea.session, 'get', side_effect=[
            MockResponse(status_code, ''),
            MockResponse(HTTPStatus.OK, '{"nfts": []}'),
        ]) as get_mock,
        patch('rotkehlchen.externalapis.opensea.cancellable_sleep') as sleep_mock,
    ):
        assert opensea._query(endpoint='assets', options=ACCOUNT_OPTIONS) == {'nfts': []}

    assert get_mock.call_count == 2
    sleep_mock.assert_called_once_with(1)


def test_other_errors_fail_without_retrying(opensea: Opensea) -> None:
    with (
        patch.object(opensea.session, 'get', return_value=MockResponse(HTTPStatus.NOT_FOUND, 'not found')) as get_mock,  # noqa: E501
        patch('rotkehlchen.externalapis.opensea.cancellable_sleep') as sleep_mock,
        pytest.raises(RemoteError, match='failed with HTTP status code 404'),
    ):
        opensea._query(endpoint='assets', options=ACCOUNT_OPTIONS)

    assert get_mock.call_count == 1
    assert sleep_mock.call_count == 0
