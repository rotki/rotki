"""Local FinTS/HBCI connector using python-fints."""
import base64
import json
from collections import defaultdict
from contextvars import ContextVar
from datetime import UTC, date, datetime
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final
from urllib.parse import urlparse

import requests
from fints.client import FinTS3PinTanClient, NeedRetryResponse, NeedTANResponse
from fints.exceptions import (
    FinTSClientError,
    FinTSClientPINError,
    FinTSClientTemporaryAuthError,
    FinTSConnectionError,
    FinTSDialogInitError,
    FinTSError,
    FinTSUnsupportedOperation,
)
from fints.models import SEPAAccount

from rotkehlchen.assets.asset import Asset
from rotkehlchen.banks.connector import BankConnector
from rotkehlchen.banks.constants import FINTS_PRODUCT_ID
from rotkehlchen.banks.errors import (
    BankAuthChallenge,
    BankAuthExpired,
    BankError,
    BankMFARequired,
    BankSchemaDrift,
)
from rotkehlchen.banks.manifest import AuthPrimitive
from rotkehlchen.banks.manifests import FINTS_MANIFEST
from rotkehlchen.banks.normalization import (
    BankAccount,
    BankTransaction,
    BankTransactionKind,
    BankTransactionSide,
    content_hash_id,
)
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    ExchangeApiCredentials,
    ExchangeAuthCredentials,
    Location,
    Timestamp,
    TimestampMS,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from mt940.models import Balance as FinTSBalance, Transaction as MT940Transaction

    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.exchange import HistoryEventQueue
    from rotkehlchen.user_messages import MessagesAggregator

SESSION_VERSION: Final = 1
DIRECT_DEBIT_CODES: Final = frozenset({'DD', 'ESDD', 'BBDD', 'NDDT'})
CARD_CODES: Final = frozenset({'CCRD', 'DCCT', 'POS', 'NPOS'})
FEE_CODES: Final = frozenset({'CHRG', 'FEE', 'NCHG', 'NCOM'})
INTEREST_CODES: Final = frozenset({'INTR', 'NINT'})


class FinTSProductRegistrationError(FinTSClientError):
    """The bank rejected rotki's FinTS product registration ID."""


class RotkiFinTS3PinTanClient(FinTS3PinTanClient):
    last_response_code: str | None = None

    def _process_response(self, dialog: Any, segment: Any, response: Any) -> None:
        if (
            isinstance(response.code, str) and
            len(response.code) == 4 and
            response.code.isdecimal()
        ):
            self.last_response_code = response.code
        if response.code == '9078':
            dialog.open = False
            raise FinTSProductRegistrationError(
                'The bank rejected the FinTS product registration (code 9078)',
            )
        super()._process_response(dialog, segment, response)


class Fints(BankConnector):
    manifest = FINTS_MANIFEST

    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
            product_id: str | None = None,
            client_factory: Callable[..., FinTS3PinTanClient] | None = None,
    ) -> None:
        super().__init__(name, api_key, secret, database, msg_aggregator)
        self._set_configuration(api_key)
        self._validate_connection(self.bank_code, self.endpoint)
        self.product_id = product_id if product_id is not None else FINTS_PRODUCT_ID
        self.client_factory = client_factory or RotkiFinTS3PinTanClient
        self._client_data: bytes | None = None
        self._pending: dict[str, Any] | None = None
        self._completed: dict[str, Any] = {}
        self._accounts: dict[str, SEPAAccount] = {}
        self._history_sync_active = ContextVar[bool]('fints_history_sync_active', default=False)
        self._restore_session()

    def _set_configuration(self, api_key: ApiKey) -> None:
        try:
            configuration = json.loads(api_key)
            self.bank_code = configuration['bank_code']
            self.endpoint = configuration['endpoint']
            self.username = configuration['username']
        except (JSONDecodeError, KeyError, TypeError) as e:
            raise BankError('Invalid stored FinTS connection configuration') from e

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        if (changed := super().edit_exchange_credentials(credentials)):
            self._set_configuration(self.api_key)
            self._validate_connection(self.bank_code, self.endpoint)
            self._client_data = None
            self._pending = None
            self._completed.clear()
            self._accounts.clear()
            with self.db.user_write() as write_cursor:
                self.clear_session(write_cursor)
        return changed

    @staticmethod
    def _validate_connection(bank_code: str, endpoint: str) -> None:
        if len(bank_code) != 8 or not bank_code.isdecimal():
            raise BankError('The FinTS bank code (BLZ) must contain exactly eight digits')
        parsed = urlparse(endpoint)
        if parsed.scheme != 'https' or parsed.hostname is None or parsed.username is not None:
            raise BankError('The FinTS endpoint must be an HTTPS URL without embedded credentials')

    @classmethod
    def api_credentials_from_values(
            cls,
            name: str,
            location: Location,
            values: dict[str, str],
            current: ExchangeAuthCredentials | None = None,
    ) -> ExchangeApiCredentials:
        existing: dict[str, str] = {}
        if current is not None and current.api_key is not None:
            try:
                existing = json.loads(current.api_key)
            except (JSONDecodeError, TypeError) as e:
                raise BankError('Invalid stored FinTS connection configuration') from e
        configuration = {
            key: values.get(key, existing.get(key))
            for key in ('bank_code', 'endpoint', 'username')
        }
        if not all(isinstance(value, str) for value in configuration.values()):
            raise BankError('FinTS requires a bank code, endpoint and username')
        bank_code, endpoint, username = (
            str(configuration[key]) for key in ('bank_code', 'endpoint', 'username')
        )
        bank_code = bank_code.strip()
        endpoint = endpoint.strip()
        cls._validate_connection(bank_code, endpoint)
        pin = values.get(
            'pin',
            current.api_secret.decode()
            if current is not None and current.api_secret is not None else None,
        )
        if pin is None:
            raise BankError('FinTS requires an online banking PIN')
        return ExchangeApiCredentials(
            name=name,
            location=location,
            api_key=ApiKey(json.dumps({
                'bank_code': bank_code,
                'endpoint': endpoint,
                'username': username,
            }, separators=(',', ':'), sort_keys=True)),
            api_secret=ApiSecret(pin.encode()),
        )

    def _restore_session(self) -> None:
        if (serialized := self.load_session()) is None:
            return
        try:
            data = json.loads(serialized)
            if data['version'] != SESSION_VERSION:
                return
            if (client_data := data.get('client_data')) is not None:
                self._client_data = base64.b64decode(client_data, validate=True)
            self._pending = data.get('pending')
        except (JSONDecodeError, KeyError, TypeError, ValueError):
            with self.db.user_write() as write_cursor:
                self.clear_session(write_cursor)

    def _save_state(self, client: FinTS3PinTanClient) -> None:
        self._client_data = client.deconstruct(including_private=True)
        data = {
            'version': SESSION_VERSION,
            'client_data': base64.b64encode(self._client_data).decode(),
            'pending': self._pending,
        }
        with self.db.user_write() as write_cursor:
            self.save_session(
                write_cursor,
                json.dumps(data, separators=(',', ':'), sort_keys=True),
            )

    def _new_client(self) -> FinTS3PinTanClient:
        if len(self.product_id) != 25:
            raise BankError(
                "rotki's 25-character FinTS product registration ID is not configured",
            )
        return self.client_factory(
            self.bank_code,
            self.username,
            self.secret.decode(),
            self.endpoint,
            product_id=self.product_id,
            from_data=self._client_data,
        )

    @staticmethod
    def _response_code_suffix(client: FinTS3PinTanClient) -> str:
        code = getattr(client, 'last_response_code', None)
        return f' (response code {code})' if isinstance(code, str) and len(code) == 4 and code.isdecimal() else ''  # noqa: E501

    @staticmethod
    def _challenge(response: NeedTANResponse) -> BankAuthChallenge:
        matrix = response.challenge_matrix
        if response.decoupled:
            primitive = AuthPrimitive.APP_APPROVAL_POLL
            prompt = response.challenge or 'Approve the request in your banking app'
        elif matrix is not None or response.challenge_hhduc is not None:
            primitive = AuthPrimitive.CHALLENGE_DISPLAY
            prompt = 'Complete the displayed bank challenge and enter the generated TAN'
        else:
            primitive = AuthPrimitive.OTP_INPUT
            prompt = response.challenge or 'Enter the TAN requested by your bank'
        return BankAuthChallenge(
            primitive=primitive,
            prompt=prompt,
            challenge=response.challenge,
            challenge_html=response.challenge_html,
            challenge_data=base64.b64encode(matrix[1]).decode() if matrix is not None else response.challenge_hhduc,  # noqa: E501
            challenge_mime_type=matrix[0] if matrix is not None else None,
        )

    def _pause_for_auth(
            self,
            client: FinTS3PinTanClient,
            response: NeedTANResponse,
            operation: str,
            request: dict[str, Any],
            during_initialization: bool,
            resume_history: bool | None = None,
    ) -> None:
        self._pending = {
            'operation': operation,
            'dialog': base64.b64encode(client.pause_dialog()).decode(),
            'retry': base64.b64encode(response.get_data()).decode(),
            'decoupled': bool(response.decoupled),
            'during_initialization': during_initialization,
            'request': request,
            'resume_history': (
                self._history_sync_active.get() if resume_history is None else resume_history
            ),
        }
        self._save_state(client)
        raise BankMFARequired(self._challenge(response))

    def _pending_response(self) -> NeedTANResponse:
        if self._pending is None:
            raise BankError('FinTS has no pending authentication request')
        try:
            retry = NeedRetryResponse.from_data(base64.b64decode(
                self._pending['retry'],
                validate=True,
            ))
            if not isinstance(retry, NeedTANResponse):
                raise TypeError('FinTS only exposes TAN retries here')
            retry.decoupled = self._pending['decoupled']
        except (KeyError, TypeError, ValueError) as e:
            raise BankError('The saved FinTS authentication request is invalid or expired') from e
        return retry

    def pending_authentication(self) -> BankAuthChallenge | None:
        return self._challenge(self._pending_response()) if self._pending is not None else None

    def pending_authentication_resumes_history(self) -> bool:
        return self._pending is not None and self._pending.get('resume_history') is True

    @staticmethod
    def _serialize_account(account: SEPAAccount) -> dict[str, str | None]:
        return {
            key: getattr(account, key)
            for key in ('iban', 'bic', 'accountnumber', 'subaccount', 'blz')
        }

    @staticmethod
    def _deserialize_account(data: dict[str, str | None]) -> SEPAAccount:
        try:
            return SEPAAccount(*(data[key] for key in (
                'iban', 'bic', 'accountnumber', 'subaccount', 'blz',
            )))
        except KeyError as e:
            raise BankError('The saved FinTS account request is invalid or expired') from e

    def _run_operation(
            self,
            client: FinTS3PinTanClient,
            operation: str,
            request: dict[str, Any],
    ) -> Any:
        if operation == 'accounts':
            return client.get_sepa_accounts()
        account = self._deserialize_account(request['account'])
        if operation.startswith('balance:'):
            return client.get_balance(account)
        if operation.startswith('transactions:'):
            return client.get_transactions(
                account,
                start_date=(
                    date.fromisoformat(start_date)
                    if (start_date := request.get('start_date')) is not None else None
                ),
                end_date=date.fromisoformat(request['end_date']),
                include_pending=False,
            )
        raise BankError('The saved FinTS operation is invalid or expired')

    def _execute(self, operation: str, request: dict[str, Any] | None = None) -> Any:
        if operation in self._completed:
            return self._completed.pop(operation)
        if self._pending is not None:
            raise BankMFARequired(self._challenge(self._pending_response()))

        client = self._new_client()
        operation_request = request or {}
        try:
            with client:
                if isinstance(client.init_tan_response, NeedTANResponse):
                    self._pause_for_auth(
                        client=client,
                        response=client.init_tan_response,
                        operation=operation,
                        request=operation_request,
                        during_initialization=True,
                    )
                result = self._run_operation(client, operation, operation_request)
                if isinstance(result, NeedTANResponse):
                    self._pause_for_auth(
                        client=client,
                        response=result,
                        operation=operation,
                        request=operation_request,
                        during_initialization=False,
                    )
        except FinTSProductRegistrationError as e:
            raise BankError(
                "The bank does not recognize rotki's FinTS product registration yet (code 9078)",
            ) from e
        except FinTSClientPINError as e:
            raise BankAuthExpired(
                f'The bank rejected FinTS authentication{self._response_code_suffix(client)}',
            ) from e
        except FinTSClientTemporaryAuthError as e:
            raise BankAuthExpired(
                f'The FinTS access is temporarily blocked{self._response_code_suffix(client)}',
            ) from e
        except FinTSDialogInitError as e:
            raise BankError(
                f'The FinTS dialog could not be initialized{self._response_code_suffix(client)}',
            ) from e
        except (FinTSConnectionError, requests.exceptions.RequestException) as e:
            raise RemoteError(f'Could not connect to the FinTS endpoint: {e!s}') from e
        except FinTSUnsupportedOperation as e:
            raise BankError(f'The bank does not support this FinTS operation: {e!s}') from e
        except FinTSError as e:
            raise BankError(f'The FinTS operation failed: {e!s}') from e
        self._pending = None
        self._save_state(client)
        return result

    def answer_authentication(self, response: str | None) -> None:
        if self._pending is None:
            raise BankError('FinTS has no pending authentication request')
        client = self._new_client()
        pending = self._pending
        try:
            retry = self._pending_response()
            if retry.decoupled is False and not response:
                raise BankError('A TAN is required to complete the FinTS authentication')
            with client.resume_dialog(base64.b64decode(pending['dialog'], validate=True)):
                result = client.send_tan(retry, '' if retry.decoupled else response)
                if isinstance(result, NeedTANResponse):
                    self._pause_for_auth(
                        client=client,
                        response=result,
                        operation=pending['operation'],
                        request=pending['request'],
                        during_initialization=pending['during_initialization'],
                        resume_history=pending.get('resume_history') is True,
                    )
                if pending['during_initialization']:
                    result = self._run_operation(
                        client=client,
                        operation=pending['operation'],
                        request=pending['request'],
                    )
                    if isinstance(result, NeedTANResponse):
                        self._pause_for_auth(
                            client=client,
                            response=result,
                            operation=pending['operation'],
                            request=pending['request'],
                            during_initialization=False,
                            resume_history=pending.get('resume_history') is True,
                        )
        except (KeyError, TypeError, ValueError) as e:
            raise BankError('The saved FinTS authentication request is invalid or expired') from e
        except (FinTSClientPINError, FinTSClientTemporaryAuthError) as e:
            raise BankAuthExpired('The TAN was rejected by the bank') from e
        except (FinTSConnectionError, requests.exceptions.RequestException) as e:
            raise RemoteError(f'Could not connect to the FinTS endpoint: {e!s}') from e
        except FinTSError as e:
            raise BankError(f'The FinTS authentication failed: {e!s}') from e

        operation = pending['operation']
        self._pending = None
        self._completed[operation] = result
        self._save_state(client)

    def _query_into_queue(
            self,
            end_ts: Timestamp,
            event_queue: HistoryEventQueue,
            force_refresh: bool,
    ) -> Timestamp:
        token = self._history_sync_active.set(True)
        try:
            return super()._query_into_queue(
                end_ts=end_ts,
                event_queue=event_queue,
                force_refresh=force_refresh,
            )
        finally:
            self._history_sync_active.reset(token)

    @staticmethod
    def _account_identifier(account: SEPAAccount) -> str:
        return account.iban or f'{account.blz}:{account.accountnumber}:{account.subaccount or ""}'

    @staticmethod
    def _resolve_fiat(symbol: str) -> AssetWithOracles:
        try:
            return Asset(symbol).resolve_to_fiat_asset()
        except (UnknownAsset, WrongAssetType) as e:
            raise BankSchemaDrift(f'FinTS returned unsupported currency {symbol}') from e

    def query_accounts(self) -> list[BankAccount]:
        accounts = self._execute('accounts')
        result: list[BankAccount] = []
        for account in accounts:
            identifier = self._account_identifier(account)
            self._accounts[identifier] = account

            balance: FinTSBalance = self._execute(
                f'balance:{identifier}',
                {'account': self._serialize_account(account)},
            )
            if (
                    (balance_amount := balance.amount) is None or
                    not hasattr(balance_amount, 'currency') or
                    not hasattr(balance_amount, 'amount') or
                    not isinstance(currency := balance_amount.currency, str)
            ):
                raise BankSchemaDrift(f'FinTS returned no balance for account {identifier}')
            result.append(BankAccount(
                identifier=identifier,
                name=account.iban or account.accountnumber,
                asset=self._resolve_fiat(currency),
                balance=FVal(balance_amount.amount),
                iban=account.iban,
            ))
        return result

    @staticmethod
    def _transaction_kind(data: dict[str, Any]) -> BankTransactionKind:
        code = str(
            data.get('purpose_code') or data.get('transaction_code') or data.get('id') or '',
        ).upper()
        if code in DIRECT_DEBIT_CODES:
            return BankTransactionKind.DIRECT_DEBIT
        if code in CARD_CODES:
            return BankTransactionKind.CARD
        if code in FEE_CODES:
            return BankTransactionKind.FEE
        if code in INTEREST_CODES:
            return BankTransactionKind.INTEREST
        return BankTransactionKind.TRANSFER

    def _deserialize_transaction(
            self,
            transaction: MT940Transaction | Any,
            account: BankAccount,
            duplicate_index: int,
    ) -> BankTransaction:
        data = transaction.data
        try:
            amount = data['amount']
            booking_date: date = data.get('date') or data['entry_date']
            timestamp = Timestamp(int(datetime.combine(booking_date, datetime.min.time(), tzinfo=UTC).timestamp()))  # noqa: E501
            signed_amount = FVal(amount.amount)
            reference = data.get('purpose') or data.get('transaction_details') or data.get('extra_details') or None  # noqa: E501
            counterparty_name = data.get('applicant_name') or None
            counterparty_account = data.get('applicant_iban') or data.get('applicant_bin') or None
            identity = content_hash_id(
                account.identifier,
                booking_date.isoformat(),
                amount.amount,
                amount.currency,
                data.get('bank_reference'),
                data.get('customer_reference'),
                counterparty_name,
                counterparty_account,
                reference,
                duplicate_index,
            )
            return BankTransaction(
                source_id=identity,
                account_id=account.identifier,
                timestamp=TimestampMS(timestamp * 1000),
                asset=self._resolve_fiat(amount.currency),
                amount=abs(signed_amount),
                side=(
                    BankTransactionSide.CREDIT
                    if signed_amount > 0 else BankTransactionSide.DEBIT
                ),
                kind=self._transaction_kind(data),
                counterparty_name=counterparty_name,
                counterparty_account=counterparty_account,
                reference=reference,
                updated_at=timestamp,
            )
        except (KeyError, TypeError, ValueError) as e:
            raise BankSchemaDrift(
                f'FinTS transaction could not be normalized: {e!s}',
                context={'keys': sorted(data)},
            ) from e

    def query_transactions(
            self,
            account: BankAccount,
            updated_since: Timestamp | None,
    ) -> list[BankTransaction]:
        if (sepa_account := self._accounts.get(account.identifier)) is None:
            raise BankError(
                f'FinTS account {account.identifier} is not present in account discovery',
            )
        start_date = datetime.fromtimestamp(updated_since, tz=UTC).date() if updated_since is not None else None  # noqa: E501
        operation = f'transactions:{account.identifier}:{start_date or "all"}'
        transactions = self._execute(operation, {
            'account': self._serialize_account(sepa_account),
            'start_date': start_date.isoformat() if start_date is not None else None,
            'end_date': datetime.now(tz=UTC).date().isoformat(),
        })
        occurrences: defaultdict[str, int] = defaultdict(int)
        result = []
        for transaction in transactions:
            raw_identity = content_hash_id(account.identifier, sorted(transaction.data.items()))
            result.append(self._deserialize_transaction(
                transaction=transaction,
                account=account,
                duplicate_index=occurrences[raw_identity],
            ))
            occurrences[raw_identity] += 1
        return result
