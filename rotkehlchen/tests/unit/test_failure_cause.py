from http import HTTPStatus

import pytest

from rotkehlchen.api.websockets.typedefs import UserMessageKey
from rotkehlchen.banks.errors import BankAuthExpired, BankRateLimited, BankSchemaDrift
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import (
    APIKeyNotAvailable,
    BlockscoutIncompleteResponse,
    ChainNotSupported,
    IncompleteTransactionsQuery,
    IndexerRangeNotCovered,
    RecoverableRemoteError,
    RemoteError,
    RequestTooLargeError,
    remote_error_for_status,
)
from rotkehlchen.exchanges.binance import BinancePermissionError


def test_failure_cause_wire_values() -> None:
    """The frontend mirrors these strings, so renaming a member is a breaking API change."""
    assert [cause.value for cause in FailureCause] == [
        'network',
        'auth',
        'bad_data',
        'local_db',
        'unsupported',
        'internal',
        'invalid_input',
        'not_found',
        'conflict',
        'forbidden',
        'rate_limited',
        'remote_rejected',
        'cancelled',
    ]


def test_failure_cause_shares_user_message_key_spelling() -> None:
    """One frontend mapping reads both lanes, so the shared causes must stay spelled alike."""
    shared = {cause.value for cause in FailureCause} & {key.value for key in UserMessageKey}
    assert shared == {'network', 'auth', 'bad_data', 'local_db', 'unsupported', 'internal'}


@pytest.mark.parametrize(('status_code', 'expected_cause', 'expected_class'), [
    (HTTPStatus.TOO_MANY_REQUESTS, FailureCause.RATE_LIMITED, RemoteError),
    (HTTPStatus.REQUEST_TIMEOUT, FailureCause.NETWORK, RecoverableRemoteError),
    (HTTPStatus.BAD_GATEWAY, FailureCause.NETWORK, RecoverableRemoteError),
    (HTTPStatus.UNAUTHORIZED, FailureCause.AUTH, RemoteError),
    (HTTPStatus.FORBIDDEN, FailureCause.REMOTE_REJECTED, RemoteError),
    (HTTPStatus.NOT_FOUND, FailureCause.REMOTE_REJECTED, RemoteError),
])
def test_remote_error_for_status(
        status_code: HTTPStatus,
        expected_cause: FailureCause,
        expected_class: type[RemoteError],
) -> None:
    """The status of a failed response decides both its cause and whether it is recoverable."""
    error = remote_error_for_status(status_code, 'failed')
    assert type(error) is expected_class
    assert error.cause == expected_cause
    assert error.error_code == status_code


@pytest.mark.parametrize(('error', 'expected_cause'), [
    (APIKeyNotAvailable('no key'), FailureCause.AUTH),
    (ChainNotSupported('no chain'), FailureCause.UNSUPPORTED),
    (IndexerRangeNotCovered('no range'), FailureCause.UNSUPPORTED),
    (BlockscoutIncompleteResponse('not indexed'), FailureCause.NETWORK),
    (IncompleteTransactionsQuery('some failed'), FailureCause.NETWORK),
    (RequestTooLargeError('too long'), FailureCause.REMOTE_REJECTED),
    (BinancePermissionError('rejected key'), FailureCause.AUTH),
    (BankAuthExpired('expired'), FailureCause.AUTH),
    (BankRateLimited('slow down'), FailureCause.RATE_LIMITED),
    (BankSchemaDrift('changed'), FailureCause.BAD_DATA),
])
def test_remote_error_subclasses_fix_their_cause(
        error: RemoteError,
        expected_cause: FailureCause,
) -> None:
    assert error.cause == expected_cause
