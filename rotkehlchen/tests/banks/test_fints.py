"""FinTS-specific session and interactive authentication behavior."""
from contextlib import contextmanager
from http import HTTPStatus
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fints.client import NeedRetryResponse, NeedTANResponse
from fints.exceptions import (
    FinTSClientPINError,
    FinTSClientTemporaryAuthError,
    FinTSDialogInitError,
)

from rotkehlchen.api.services.banks import BanksService
from rotkehlchen.banks.errors import BankAuthExpired, BankError, BankMFARequired
from rotkehlchen.banks.fints import (
    Fints,
    FinTSProductRegistrationError,
    RotkiFinTS3PinTanClient,
)
from rotkehlchen.banks.manager import BankManager
from rotkehlchen.banks.manifest import AuthPrimitive
from rotkehlchen.banks.normalization import BankTransactionKind
from rotkehlchen.tests.utils.banks import FinTSFixtureTransport
from rotkehlchen.types import ExchangeApiCredentials, Location

PRODUCT_ID = '0123456789012345678901234'
FINTS_VALUES = {
    'bank_code': '12030000',
    'endpoint': 'https://bank.example/fints',
    'username': 'test-login',
    'pin': 'secret-pin',
}


@pytest.mark.parametrize(('code', 'expected_kind'), [
    ('NDDT', BankTransactionKind.DIRECT_DEBIT),
    ('NPOS', BankTransactionKind.CARD),
    ('NCHG', BankTransactionKind.FEE),
    ('NINT', BankTransactionKind.INTEREST),
])
def test_mt940_transaction_kinds(code: str, expected_kind: BankTransactionKind) -> None:
    assert Fints._transaction_kind({'id': code}) == expected_kind


class FixtureTANResponse(NeedTANResponse):
    def __init__(  # pylint: disable=super-init-not-called
            self,
            decoupled: bool = False,
            matrix: tuple[str, bytes] | None = None,
    ) -> None:
        self.challenge = 'Authorize account access'
        self.challenge_html = '<p>Authorize account access</p>'
        self.challenge_hhduc = None
        self.challenge_matrix = matrix
        self.decoupled = decoupled

    def get_data(self) -> bytes:
        return b'retry-state'


class AuthenticationTransport(FinTSFixtureTransport):
    def __init__(self, challenge: FixtureTANResponse, pending_polls: int = 0) -> None:
        super().__init__()
        self.challenge = challenge
        self.challenge_sent = False
        self.answers: list[str] = []
        self.pending_polls = pending_polls

    def get_sepa_accounts(self):
        if self.challenge_sent is False:
            self.challenge_sent = True
            return self.challenge
        return super().get_sepa_accounts()

    def pause_dialog(self) -> bytes:
        return b'dialog-state'

    @contextmanager
    def resume_dialog(self, dialog_data: bytes):
        assert dialog_data == b'dialog-state'
        yield self

    def send_tan(self, challenge: NeedTANResponse, tan: str):
        self.answers.append(tan)
        if self.pending_polls > 0:
            self.pending_polls -= 1
            return challenge
        return super().get_sepa_accounts()


class InitializationAuthenticationTransport(FinTSFixtureTransport):
    def __init__(self, challenge: FixtureTANResponse) -> None:
        super().__init__()
        self.challenge = challenge
        self.initialization_answered = False
        self.answers: list[str] = []

    def __enter__(self) -> None:
        self.init_tan_response = None if self.initialization_answered else self.challenge

    def pause_dialog(self) -> bytes:
        return b'initialization-dialog-state'

    @contextmanager
    def resume_dialog(self, dialog_data: bytes):
        assert dialog_data == b'initialization-dialog-state'
        yield self

    def send_tan(self, _challenge: NeedTANResponse, tan: str) -> object:
        self.answers.append(tan)
        self.initialization_answered = True
        self.init_tan_response = None
        return object()


class UnregisteredProductTransport(FinTSFixtureTransport):
    def __enter__(self) -> None:
        raise FinTSProductRegistrationError('code 9078')


class FailedInitializationTransport(FinTSFixtureTransport):
    def __init__(self, error: Exception, response_code: str) -> None:
        super().__init__()
        self.error = error
        self.last_response_code = response_code

    def __enter__(self) -> None:
        raise self.error


def create_fints(database, messages, transport: FinTSFixtureTransport) -> Fints:
    credentials = Fints.api_credentials_from_values(
        name='FinTS 1',
        location=Location.FINTS,
        values=FINTS_VALUES,
    )
    assert credentials.api_secret is not None
    return Fints(
        name=credentials.name,
        api_key=credentials.api_key,
        secret=credentials.api_secret,
        database=database,
        msg_aggregator=messages,
        product_id=PRODUCT_ID,
        client_factory=transport,
    )


def test_product_id_and_client_state_are_used_on_every_dialog(
        database,
        function_scope_messages_aggregator,
) -> None:
    transport = FinTSFixtureTransport()
    connector = create_fints(database, function_scope_messages_aggregator, transport)
    connector.query_accounts()
    assert set(transport.product_ids) == {PRODUCT_ID}
    assert transport.restored_client_data[0] is None
    assert all(
        value == b'fixture-client-state-private'
        for value in transport.restored_client_data[1:]
    )

    restored_transport = FinTSFixtureTransport()
    restored = create_fints(database, function_scope_messages_aggregator, restored_transport)
    restored.query_accounts()
    assert restored_transport.restored_client_data[0] == b'fixture-client-state-private'


def test_unregistered_product_error_is_reported(
        database,
        function_scope_messages_aggregator,
) -> None:
    connector = create_fints(
        database,
        function_scope_messages_aggregator,
        UnregisteredProductTransport(),
    )

    with pytest.raises(BankError, match=r'does not recognize.*yet'):
        connector.query_accounts()


def test_product_registration_response_aborts_the_dialog() -> None:
    client = object.__new__(RotkiFinTS3PinTanClient)
    with pytest.raises(FinTSProductRegistrationError):
        client._process_response(  # pylint: disable=protected-access
            dialog=(dialog := SimpleNamespace(open=True)),
            segment=None,
            response=SimpleNamespace(code='9078'),
        )

    assert dialog.open is False


@pytest.mark.parametrize(('error', 'response_code', 'expected_exception', 'message'), [
    (
        FinTSClientPINError('generic library message'),
        '9942',
        BankAuthExpired,
        r'rejected FinTS authentication \(response code 9942\)',
    ),
    (
        FinTSClientTemporaryAuthError('generic library message'),
        '3938',
        BankAuthExpired,
        r'temporarily blocked \(response code 3938\)',
    ),
    (
        FinTSDialogInitError('generic library message'),
        '9800',
        BankError,
        r'could not be initialized \(response code 9800\)',
    ),
])
def test_initialization_errors_preserve_safe_response_code(
        database,
        function_scope_messages_aggregator,
        error: Exception,
        response_code: str,
        expected_exception: type[BankError],
        message: str,
) -> None:
    connector = create_fints(
        database,
        function_scope_messages_aggregator,
        FailedInitializationTransport(error=error, response_code=response_code),
    )

    with pytest.raises(expected_exception, match=message):
        connector.query_accounts()


def test_fints_endpoint_whitespace_is_removed() -> None:
    credentials = Fints.api_credentials_from_values(
        name='FinTS 1',
        location=Location.FINTS,
        values={**FINTS_VALUES, 'endpoint': ' https://bank.example/fints '},
    )

    assert 'https://bank.example/fints' in credentials.api_key
    assert ' https://bank.example/fints ' not in credentials.api_key


@pytest.mark.parametrize(('challenge', 'primitive', 'answer'), [
    (FixtureTANResponse(), AuthPrimitive.OTP_INPUT, '123456'),
    (FixtureTANResponse(decoupled=True), AuthPrimitive.APP_APPROVAL_POLL, ''),
    (
        FixtureTANResponse(matrix=('image/png', b'photo-tan-image')),
        AuthPrimitive.CHALLENGE_DISPLAY,
        '654321',
    ),
])
def test_tan_challenges_resume_the_paused_dialog(
        database,
        function_scope_messages_aggregator,
        challenge: FixtureTANResponse,
        primitive: AuthPrimitive,
        answer: str,
) -> None:
    transport = AuthenticationTransport(challenge)
    connector = create_fints(database, function_scope_messages_aggregator, transport)
    with pytest.raises(BankMFARequired) as exc_info:
        connector.query_accounts()
    assert exc_info.value.challenge.primitive == primitive
    assert (session := connector.load_session()) is not None
    assert 'secret-pin' not in session

    with patch.object(NeedRetryResponse, 'from_data', return_value=challenge):
        with pytest.raises(BankMFARequired) as exc_info:
            connector.query_accounts()
        assert exc_info.value.challenge.primitive == primitive
        connector.answer_authentication(answer or None)
    assert transport.answers == [answer]
    assert len(connector.query_accounts()) == 1


def test_decoupled_approval_can_be_polled_without_restarting(
        database,
        function_scope_messages_aggregator,
) -> None:
    challenge = FixtureTANResponse(decoupled=True)
    transport = AuthenticationTransport(challenge, pending_polls=1)
    connector = create_fints(database, function_scope_messages_aggregator, transport)
    with pytest.raises(BankMFARequired):
        connector.query_accounts()

    with patch.object(NeedRetryResponse, 'from_data', return_value=challenge):
        with pytest.raises(BankMFARequired) as exc_info:
            connector.answer_authentication(None)
        assert exc_info.value.challenge.primitive == AuthPrimitive.APP_APPROVAL_POLL
        connector.answer_authentication(None)

    assert transport.answers == ['', '']
    assert len(connector.query_accounts()) == 1


def test_dialog_initialization_tan_runs_the_operation_in_the_resumed_dialog(
        database,
        function_scope_messages_aggregator,
) -> None:
    challenge = FixtureTANResponse()
    transport = InitializationAuthenticationTransport(challenge)
    connector = create_fints(database, function_scope_messages_aggregator, transport)
    with pytest.raises(BankMFARequired):
        connector.query_accounts()

    with patch.object(NeedRetryResponse, 'from_data', return_value=challenge):
        connector.answer_authentication('123456')

    assert transport.answers == ['123456']
    assert len(connector.query_accounts()) == 1
    assert [request for request, _params in transport.requests].count('accounts') == 1


def test_query_authentication_is_exposed_and_cleared_by_the_bank_manager(
        database,
        function_scope_messages_aggregator,
) -> None:
    challenge = FixtureTANResponse()
    connector = create_fints(
        database,
        function_scope_messages_aggregator,
        AuthenticationTransport(challenge),
    )
    manager = BankManager(function_scope_messages_aggregator)
    manager.connected_banks[Location.FINTS].append(connector)

    with pytest.raises(BankMFARequired):
        manager.query_bank_history_events(location=Location.FINTS, name=connector.name)
    assert manager.sync_status[connector.location_id()].auth_challenge is not None

    restored_transport = AuthenticationTransport(challenge)
    restored = create_fints(database, function_scope_messages_aggregator, restored_transport)
    restored_manager = BankManager(function_scope_messages_aggregator)
    credentials = ExchangeApiCredentials(
        name=restored.name,
        location=restored.location,
        api_key=restored.api_key,
        api_secret=restored.secret,
    )
    with patch.object(NeedRetryResponse, 'from_data', return_value=challenge):
        with patch.object(restored_manager, '_instantiate', return_value=restored):
            restored_manager.initialize_banks(
                credentials={Location.FINTS: [credentials]},
                database=database,
            )
        assert restored_manager.sync_status[restored.location_id()].auth_challenge is not None
        assert restored_manager.answer_bank_authentication(
            name=restored.name,
            location=restored.location,
            response='123456',
        ) == (True, '')
    assert restored_transport.answers == ['123456']
    status = restored_manager.sync_status[restored.location_id()]
    assert status.auth_challenge is None
    assert status.last_sync_ts is not None
    assert any(request == 'transactions' for request, _params in restored_transport.requests)


def test_sync_requiring_authentication_has_no_success_result(
        database,
        function_scope_messages_aggregator,
) -> None:
    connector = create_fints(
        database,
        function_scope_messages_aggregator,
        AuthenticationTransport(FixtureTANResponse()),
    )
    manager = BankManager(function_scope_messages_aggregator)
    manager.connected_banks[Location.FINTS].append(connector)

    rotki = MagicMock()
    rotki.bank_manager = manager
    result = BanksService(rotki).sync_banks(
        location=Location.FINTS,
        name=connector.name,
    )

    assert result['result'] is None
    assert result['status_code'] == HTTPStatus.ACCEPTED
