from rotkehlchen.api.websockets.typedefs import UserMessageKey
from rotkehlchen.errors.cause import FailureCause


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
