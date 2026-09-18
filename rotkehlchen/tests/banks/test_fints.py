"""FinTS-specific session and interactive authentication behavior."""
from contextlib import contextmanager
from datetime import timedelta
from http import HTTPStatus
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fints.client import FinTS3PinTanClient, NeedRetryResponse, NeedTANResponse
from fints.exceptions import (
    FinTSClientPINError,
    FinTSClientTemporaryAuthError,
    FinTSDialogInitError,
)
from fints.formals import UserDefinedSignature
from fints.parser import FinTS3Parser
from fints.utils import Password, mt940_to_array

from rotkehlchen.api.services.banks import BanksService
from rotkehlchen.banks.constants import FINTS_CONNECTOR
from rotkehlchen.banks.errors import (
    BankAuthChallenge,
    BankAuthExpired,
    BankError,
    BankMFARequired,
)
from rotkehlchen.banks.fints import (
    Fints,
    FinTSProductRegistrationError,
    RotkiFinTS3PinTanClient,
)
from rotkehlchen.banks.manager import BankCredentialInput, BankManager, BankSyncStatus
from rotkehlchen.banks.manifest import AuthPrimitive
from rotkehlchen.banks.normalization import BankTransactionKind
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.tests.utils.banks import FinTSFixtureTransport
from rotkehlchen.types import ExchangeApiCredentials

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


def test_mt940_keeps_iban_separate_from_applicant_name() -> None:
    transactions = mt940_to_array(
        ':20:START\n'
        ':25:123456789\n'
        ':28C:1/1\n'
        ':60F:C260916EUR10,00\n'
        ':61:2609160916D10,00NTRFNONREF\n'
        ':86:020?00UEBERWEISUNG?31DE02120300000000202051?32Eleftherios Karapetsas\n'
        ':62F:C260916EUR0,00\n',
    )

    assert transactions[0].data['applicant_iban'] == 'DE02120300000000202051'
    assert transactions[0].data['applicant_name'] == 'Eleftherios Karapetsas'


def test_mt940_parser_fix_preserves_transaction_identity(
        database,
        function_scope_messages_aggregator,
) -> None:
    connector = create_fints(
        database,
        function_scope_messages_aggregator,
        transport := FinTSFixtureTransport(),
    )
    account = connector.query_accounts()[0]
    parsed_transaction = SimpleNamespace(data={
        'date': (booking_date := transport.get_transactions(
            connector._accounts[account.identifier],  # pylint: disable=protected-access
        )[0].data['date']),
        'amount': (amount := SimpleNamespace(amount='-10', currency='EUR')),
        'applicant_iban': 'DE02120300000000202051',
        'applicant_name': 'Eleftherios Karapetsas',
    })
    legacy_transaction = SimpleNamespace(data={
        'date': booking_date,
        'amount': amount,
        'applicant_name': 'DE02120300000000202051Eleftherios Karapetsas',
    })

    assert connector._deserialize_transaction(  # pylint: disable=protected-access
        transaction=parsed_transaction,
        account=account,
        duplicate_index=0,
    ).source_id == connector._deserialize_transaction(  # pylint: disable=protected-access
        transaction=legacy_transaction,
        account=account,
        duplicate_index=0,
    ).source_id


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


def rotki_client_stub() -> RotkiFinTS3PinTanClient:
    """The client attributes python-fints' _process_response reads before raising for a PIN"""
    client = object.__new__(RotkiFinTS3PinTanClient)
    client.pin = Password(FINTS_VALUES['pin'])
    client._bootstrap_mode = False  # pylint: disable=protected-access
    client.bank_identifier = SimpleNamespace(bank_code=FINTS_VALUES['bank_code'])
    return client


def reject_pin(client: RotkiFinTS3PinTanClient, dialog: SimpleNamespace) -> None:
    """The bank answers 9340: python-fints blocks the client's PIN and raises"""
    client._process_response(  # pylint: disable=protected-access
        dialog=dialog,
        segment=None,
        response=SimpleNamespace(code='9340'),
    )


class RejectingAuthenticationTransport(AuthenticationTransport):
    """Rejects the first TAN it is sent the way python-fints does. The resumed dialog signs with
    the copy of the PIN its pause pickled, which the block does not reach, so leaving it while
    still open sends HKEND with the PIN python-fints just blocked."""
    def __init__(self, challenge: FixtureTANResponse) -> None:
        super().__init__(challenge)
        self.client = rotki_client_stub()
        self.dialog = SimpleNamespace(open=True)
        self.hkend_sent = False

    @contextmanager
    def resume_dialog(self, dialog_data: bytes):
        assert dialog_data == b'dialog-state'
        self.dialog.open = True
        try:
            yield self
        finally:
            if self.dialog.open:  # FinTSDialog.__exit__ ends an open dialog with HKEND
                self.hkend_sent = True
                self.dialog.open = False

    def send_tan(self, challenge: NeedTANResponse, tan: str):
        if len(self.answers) == 0:
            self.answers.append(tan)
            reject_pin(self.client, self.dialog)
        return super().send_tan(challenge, tan)


class WrongPinTransport(FinTSFixtureTransport):
    """Refuses the PIN in a fresh dialog. Its mechanism signs with the client's own PIN, so
    ending the dialog after the block raises python-fints' bare Exception over the PIN error."""
    def __init__(self) -> None:
        super().__init__()
        self.client = rotki_client_stub()
        self.dialog = SimpleNamespace(open=False)

    def __enter__(self) -> None:
        self.dialog.open = True

    def __exit__(self, *_args: object) -> None:
        if self.dialog.open:  # FinTSDialog.end() signs HKEND
            UserDefinedSignature(pin=self.client.pin, tan=None)
            self.dialog.open = False

    def get_sepa_accounts(self):
        reject_pin(self.client, self.dialog)


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
        location=FINTS_CONNECTOR,
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


@pytest.mark.parametrize(('code', 'error'), [
    ('9340', FinTSClientPINError),
    ('3938', FinTSClientTemporaryAuthError),
])
def test_rejected_authentication_closes_the_dialog_before_the_blocked_pin_signs(
        code: str,
        error: type[Exception],
) -> None:
    client = object.__new__(RotkiFinTS3PinTanClient)
    client.pin = Password(FINTS_VALUES['pin'])
    client._bootstrap_mode = False  # pylint: disable=protected-access
    client.bank_identifier = SimpleNamespace(bank_code=FINTS_VALUES['bank_code'])
    with pytest.raises(error):
        client._process_response(  # pylint: disable=protected-access
            dialog=(dialog := SimpleNamespace(open=True)),
            segment=None,
            response=SimpleNamespace(code=code),
        )

    assert dialog.open is False, 'an open dialog would sign HKEND with the blocked PIN'
    with pytest.raises(Exception, match='Refusing to use PIN after block'):
        UserDefinedSignature(pin=client.pin, tan=None)


def test_wrong_pin_in_a_fresh_dialog_reports_the_rejection(
        database,
        function_scope_messages_aggregator,
) -> None:
    """Without the dialog closed first, ending it would sign HKEND with the blocked PIN and a bare
    Exception would replace the rejection, escaping every handler as a crash."""
    connector = create_fints(database, function_scope_messages_aggregator, WrongPinTransport())

    with pytest.raises(BankAuthExpired, match='rejected FinTS authentication'):
        connector.query_accounts()


def test_ing_uses_one_step_authentication() -> None:
    client = object.__new__(RotkiFinTS3PinTanClient)
    client.bank_identifier = SimpleNamespace(bank_code='50010517')

    with patch.object(FinTS3PinTanClient, '_process_response') as process_response:
        client._process_response(  # pylint: disable=protected-access
            dialog=SimpleNamespace(open=True),
            segment=None,
            response=SimpleNamespace(code='3920'),
        )

    process_response.assert_not_called()
    assert client.last_response_code == '3920'
    assert client.is_tan_media_required() is False


def test_ing_initial_transaction_sync_requests_full_available_history(
        database,
        function_scope_messages_aggregator,
) -> None:
    transport = FinTSFixtureTransport()
    credentials = Fints.api_credentials_from_values(
        name='ING',
        location=FINTS_CONNECTOR,
        values={**FINTS_VALUES, 'bank_code': '50010517'},
    )
    assert credentials.api_secret is not None
    connector = Fints(
        name=credentials.name,
        api_key=credentials.api_key,
        secret=credentials.api_secret,
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        product_id=PRODUCT_ID,
        client_factory=transport,
    )

    account = connector.query_accounts()[0]
    connector.query_transactions(account=account, updated_since=None)

    params = next(params for request, params in transport.requests if request == 'transactions')
    assert params['end_date'] - params['start_date'] == timedelta(days=90)


def test_initial_transaction_sync_uses_bank_parameter_retention(
        database,
        function_scope_messages_aggregator,
) -> None:
    transport = FinTSFixtureTransport()
    connector = create_fints(database, function_scope_messages_aggregator, transport)
    account = connector.query_accounts()[0]
    client = SimpleNamespace(bpd=FinTS3Parser().parse_message(
        b"HIKAZS:11:6:5+1+2+1+60:J:J'",
    ))

    connector._update_retention_days(client)  # pylint: disable=protected-access
    connector.query_transactions(account=account, updated_since=None)

    params = next(params for request, params in transport.requests if request == 'transactions')
    assert connector.history_retention_days() == 60
    assert params['end_date'] - params['start_date'] == timedelta(days=60)


def test_other_banks_process_tan_mechanisms_normally() -> None:
    client = object.__new__(RotkiFinTS3PinTanClient)
    client.bank_identifier = SimpleNamespace(bank_code='12030000')
    dialog = SimpleNamespace(open=True)
    response = SimpleNamespace(code='3920')

    with (
        patch.object(FinTS3PinTanClient, '_process_response') as process_response,
        patch.object(FinTS3PinTanClient, 'is_tan_media_required', return_value=True),
    ):
        client._process_response(  # pylint: disable=protected-access
            dialog=dialog,
            segment=None,
            response=response,
        )
        assert client.is_tan_media_required() is True

    process_response.assert_called_once_with(dialog, None, response)


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
        location=FINTS_CONNECTOR,
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
    manager.connected_banks[FINTS_CONNECTOR].append(connector)

    with pytest.raises(BankMFARequired):
        manager.query_bank_history_events(location=FINTS_CONNECTOR, name=connector.name)
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
                credentials={FINTS_CONNECTOR: [credentials]},
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


def test_rejected_tan_drops_the_pending_challenge_and_marks_it_expired(
        database,
        function_scope_messages_aggregator,
) -> None:
    challenge = FixtureTANResponse()
    transport = RejectingAuthenticationTransport(challenge)
    connector = create_fints(database, function_scope_messages_aggregator, transport)
    manager = BankManager(function_scope_messages_aggregator)
    manager.connected_banks[FINTS_CONNECTOR].append(connector)

    with pytest.raises(BankMFARequired):
        manager.query_bank_history_events(location=FINTS_CONNECTOR, name=connector.name)
    with (
        patch.object(NeedRetryResponse, 'from_data', return_value=challenge),
        pytest.raises(BankAuthExpired),
    ):
        manager.answer_bank_authentication(
            name=connector.name,
            location=connector.location,
            response='000000',
        )

    assert transport.hkend_sent is False, 'HKEND would send the PIN python-fints just blocked'
    status = manager.sync_status[connector.location_id()]
    assert status.auth_challenge is None
    assert status.auth_expired is True
    assert status.serialize()['auth_expired'] is True
    assert connector.pending_authentication() is None
    assert '"pending":null' in (connector.load_session() or '')

    transport.challenge_sent = False
    with pytest.raises(BankMFARequired):
        manager.query_bank_history_events(location=FINTS_CONNECTOR, name=connector.name)
    assert (serialized := status.serialize())['auth_challenge'] is not None
    assert serialized['auth_expired'] is False


def test_starting_over_drops_the_pending_challenge_so_the_bank_is_asked_again(
        database,
        function_scope_messages_aggregator,
) -> None:
    """A TAN the user will not answer would otherwise be raised again by every query until it is
    answered, since only the bank knows when it lapsed."""
    challenge = FixtureTANResponse()
    transport = AuthenticationTransport(challenge)
    connector = create_fints(database, function_scope_messages_aggregator, transport)
    manager = BankManager(function_scope_messages_aggregator)
    manager.connected_banks[FINTS_CONNECTOR].append(connector)
    with pytest.raises(BankMFARequired):
        manager.query_bank_history_events(location=FINTS_CONNECTOR, name=connector.name)

    rotki = MagicMock()
    rotki.bank_manager = manager
    assert BanksService(rotki).cancel_authentication(
        name=connector.name,
        location=connector.location,
    ) == (True, '', HTTPStatus.OK)

    assert connector.has_pending_authentication() is False
    assert '"pending":null' in (connector.load_session() or '')
    status = manager.sync_status[connector.location_id()].serialize()
    assert (status['auth_challenge'], status['auth_expired']) == (None, False)
    assert len(connector.query_accounts()) == 1, 'a fresh dialog, not the saved challenge again'
    assert transport.answers == []


def test_starting_over_without_a_pending_challenge_saves_nothing(
        database,
        function_scope_messages_aggregator,
) -> None:
    connector = create_fints(
        database,
        function_scope_messages_aggregator,
        AuthenticationTransport(FixtureTANResponse()),
    )
    connector.cancel_authentication()
    assert connector.load_session() is None


def test_starting_over_a_setup_drops_it(
        database,
        function_scope_messages_aggregator,
) -> None:
    connector = create_fints(
        database,
        function_scope_messages_aggregator,
        AuthenticationTransport(FixtureTANResponse()),
    )
    manager = BankManager(function_scope_messages_aggregator)
    with pytest.raises(BankMFARequired):
        connector.query_accounts()
    manager.pending_setups[location_id := connector.location_id()] = connector

    assert manager.cancel_bank_authentication(name=connector.name, location=connector.location)

    assert location_id not in manager.pending_setups
    assert location_id not in manager.sync_status
    assert connector.load_session() is None, 'a new setup under this name would restore it'
    assert not manager.cancel_bank_authentication(name=connector.name, location=connector.location)


def test_a_further_setup_challenge_leaves_no_status_behind(
        database,
        function_scope_messages_aggregator,
) -> None:
    """A setup's challenges reach its dialog through the 202, not the connection status. A status
    recorded for one would outlive a dropped setup and show its dead challenge on a connection
    added later under the same name."""
    challenge = FixtureTANResponse(decoupled=True)
    connector = create_fints(
        database,
        function_scope_messages_aggregator,
        AuthenticationTransport(challenge, pending_polls=1),
    )
    manager = BankManager(function_scope_messages_aggregator)
    with pytest.raises(BankMFARequired):
        connector.query_accounts()
    manager.pending_setups[location_id := connector.location_id()] = connector

    with (
        patch.object(NeedRetryResponse, 'from_data', return_value=challenge),
        pytest.raises(BankMFARequired),
    ):
        manager.answer_bank_authentication(
            name=connector.name,
            location=connector.location,
            response=None,
        )
    assert manager.cancel_bank_authentication(name=connector.name, location=connector.location)

    assert location_id not in manager.sync_status


@pytest.mark.parametrize('restarted', [False, True])
def test_adding_a_connection_again_does_not_resume_an_abandoned_setup(
        database,
        function_scope_messages_aggregator,
        restarted: bool,
) -> None:
    """A setup left at its TAN (dialog closed, or rotki restarted since) kept its session, which
    the next connector under that name restored: adding it again raised the old challenge."""
    abandoned = create_fints(
        database,
        function_scope_messages_aggregator,
        AuthenticationTransport(FixtureTANResponse()),
    )
    with pytest.raises(BankMFARequired):
        abandoned.query_accounts()
    manager = BankManager(function_scope_messages_aggregator)
    if not restarted:
        manager.pending_setups[abandoned.location_id()] = abandoned

    added = create_fints(database, function_scope_messages_aggregator, FinTSFixtureTransport())
    assert added.has_pending_authentication(), 'restored from the abandoned setup'
    with patch.object(manager, '_instantiate', return_value=added):
        assert manager.setup_bank(
            name=added.name,
            location=FINTS_CONNECTOR,
            credentials=BankCredentialInput(values=FINTS_VALUES),
            database=database,
        ) == (True, '')

    assert manager.pending_setups == {}
    assert manager.get_bank(name=added.name, location=FINTS_CONNECTOR) is added


def test_answer_endpoint_reports_a_dropped_challenge_as_gone(
        database,
        function_scope_messages_aggregator,
) -> None:
    """A dropped challenge cannot be answered again, so the endpoint says so with its own status
    rather than the 409 of an answer that can be retried."""
    challenge = FixtureTANResponse()
    transport = RejectingAuthenticationTransport(challenge)
    connector = create_fints(database, function_scope_messages_aggregator, transport)
    manager = BankManager(function_scope_messages_aggregator)
    manager.connected_banks[FINTS_CONNECTOR].append(connector)
    rotki = MagicMock()
    rotki.bank_manager = manager
    with pytest.raises(BankMFARequired):
        manager.query_bank_history_events(location=FINTS_CONNECTOR, name=connector.name)

    with patch.object(NeedRetryResponse, 'from_data', return_value=challenge):
        result, message, status = BanksService(rotki).answer_authentication(
            name=connector.name,
            location=connector.location,
            response='000000',
        )

    assert (result, status) == (None, HTTPStatus.GONE)
    assert 'rejected' in message


def test_accepted_tan_stays_accepted_when_the_resumed_sync_fails(
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
    manager.connected_banks[FINTS_CONNECTOR].append(connector)
    with pytest.raises(BankMFARequired):
        manager.query_bank_history_events(location=FINTS_CONNECTOR, name=connector.name)

    with (
        patch.object(NeedRetryResponse, 'from_data', return_value=challenge),
        patch.object(connector, 'pending_authentication_resumes_history', return_value=True),
        patch.object(connector, 'query_history_events', side_effect=RemoteError('bank down')),
    ):
        assert manager.answer_bank_authentication(
            name=connector.name,
            location=connector.location,
            response='123456',
        ) == (True, '')

    status = manager.sync_status[connector.location_id()].serialize()
    assert status['auth_challenge'] is None
    assert 'bank down' in status['last_error']


def test_dropping_a_challenge_reads_whether_it_is_pending_under_the_status_lock() -> None:
    """A sync raises its challenge through set_challenge, which takes the same lock, so a challenge
    raised while a balance query decides to drop the old one is kept."""
    status = BankSyncStatus()
    status.set_challenge(challenge := BankAuthChallenge(
        primitive=AuthPrimitive.OTP_INPUT,
        prompt='Enter the TAN',
    ))

    status.drop_challenge(still_pending=status.lock.locked)
    assert status.auth_challenge == challenge

    status.drop_challenge(still_pending=lambda: False)
    assert status.serialize()['auth_challenge'] is None


def test_rejected_setup_tan_drops_the_setup_without_a_connection_status(
        database,
        function_scope_messages_aggregator,
) -> None:
    challenge = FixtureTANResponse()
    connector = create_fints(
        database,
        function_scope_messages_aggregator,
        RejectingAuthenticationTransport(challenge),
    )
    manager = BankManager(function_scope_messages_aggregator)
    with pytest.raises(BankMFARequired):
        connector.query_accounts()
    manager.pending_setups[location_id := connector.location_id()] = connector

    with (
        patch.object(NeedRetryResponse, 'from_data', return_value=challenge),
        pytest.raises(BankAuthExpired),
    ):
        manager.answer_bank_authentication(
            name=connector.name,
            location=connector.location,
            response='000000',
        )

    assert location_id not in manager.pending_setups
    assert location_id not in manager.sync_status
    assert connector.load_session() is None, 'a new setup under this name would restore it'


def test_setup_refused_after_its_answer_drops_the_setup_as_gone(
        database,
        function_scope_messages_aggregator,
) -> None:
    """The accepted answer is used up, so a 409 would invite a retry that can only fail"""
    challenge = FixtureTANResponse()
    connector = create_fints(
        database,
        function_scope_messages_aggregator,
        AuthenticationTransport(challenge),
    )
    manager = BankManager(function_scope_messages_aggregator)
    with pytest.raises(BankMFARequired):
        connector.query_accounts()
    manager.pending_setups[location_id := connector.location_id()] = connector
    rotki = MagicMock()
    rotki.bank_manager = manager

    with (
        patch.object(NeedRetryResponse, 'from_data', return_value=challenge),
        patch.object(connector, 'validate_api_key', return_value=(False, refusal := 'No login')),
    ):
        result, message, status = BanksService(rotki).answer_authentication(
            name=connector.name,
            location=connector.location,
            response='123456',
        )

    assert (result, message, status) == (None, refusal, HTTPStatus.GONE)
    assert location_id not in manager.pending_setups
    assert location_id not in manager.sync_status
    assert connector.load_session() is None, 'a new setup under this name would restore it'


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
    manager.connected_banks[FINTS_CONNECTOR].append(connector)

    rotki = MagicMock()
    rotki.bank_manager = manager
    result = BanksService(rotki).sync_banks(
        location=FINTS_CONNECTOR,
        name=connector.name,
    )

    assert result['result'] is None
    assert result['status_code'] == HTTPStatus.ACCEPTED
