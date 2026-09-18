"""Test kit for bank connectors.

A kit is everything the framework-level contract tests need to run a connector against its
committed, redacted fixtures: how to build it, a transport serving the fixtures the way the
bank's API would, and the numbers the fixtures are expected to produce.
"""
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from unittest.mock import _patch, patch
from urllib.parse import urlparse

from fints.exceptions import FinTSClientPINError, FinTSConnectionError
from fints.models import SEPAAccount

from rotkehlchen.banks.constants import FINTS_CONNECTOR
from rotkehlchen.banks.fints import Fints
from rotkehlchen.banks.qonto import Qonto
from rotkehlchen.constants.assets import A_EUR
from rotkehlchen.fval import FVal
from rotkehlchen.locations.constants import (
    LOCATION_QONTO,
)
from rotkehlchen.tests.utils.mock import MockResponse

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.banks.connector import BankConnector
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.locations.types import LocationIdentifier
    from rotkehlchen.user_messages import MessagesAggregator

BANK_FIXTURES_DIR = Path(__file__).resolve().parent.parent / 'data' / 'banks'


class FixtureTransport:
    """Stands in for `requests.Session.get`. Records every request and can be forced to
    answer everything with one response, to exercise the error mapping."""

    def __init__(self) -> None:
        self.requests: list[tuple[str, dict[str, Any]]] = []
        self.forced_response: MockResponse | None = None

    def force(self, status_code: int, text: str, headers: dict[str, str] | None = None) -> None:
        self.forced_response = MockResponse(status_code=status_code, text=text, headers=headers)

    def __call__(self, url: str, params: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        path = urlparse(url).path
        self.requests.append((path, dict(params or {})))
        if self.forced_response is not None:
            return self.forced_response
        return self.route(path, dict(params or {}))

    def route(self, path: str, params: dict[str, Any]) -> MockResponse:
        raise NotImplementedError


class QontoFixtureTransport(FixtureTransport):
    """Serves the Qonto fixtures with the API's pagination, status filter, updated_at_from
    filter and sort_by, so cursor semantics can be tested for real."""

    def __init__(self) -> None:
        super().__init__()
        fixtures = BANK_FIXTURES_DIR / 'qonto'
        self.organization = json.loads((fixtures / 'organization.json').read_text(encoding='utf8'))
        self.transactions = json.loads((fixtures / 'transactions.json').read_text(encoding='utf8'))['transactions']  # noqa: E501
        self.transactions += json.loads((fixtures / 'transactions_declined.json').read_text(encoding='utf8'))['transactions']  # noqa: E501

    def route(self, path: str, params: dict[str, Any]) -> MockResponse:
        if path.endswith('/organization'):
            return MockResponse(200, json.dumps(self.organization))
        if not path.endswith('/transactions'):
            return MockResponse(404, '{"errors":[{"code":"not_found"}]}')

        account_id = params.get('bank_account_id')
        if account_id is None:
            return MockResponse(422, '{"errors":[{"code":"missing_selector"}]}')
        rows = [t for t in self.transactions if t['bank_account_id'] == account_id]
        statuses = params.get('status[]')
        if statuses is not None:
            wanted = {statuses} if isinstance(statuses, str) else set(statuses)
            rows = [t for t in rows if t['status'] in wanted]
        else:  # the real API hides declined ones by default
            rows = [t for t in rows if t['status'] == 'completed']
        if (updated_from := params.get('updated_at_from')) is not None:
            since = datetime.strptime(updated_from, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=UTC)
            rows = [
                t for t in rows
                if datetime.fromisoformat(t['updated_at']) >= since
            ]
        sort_by = params.get('sort_by', 'settled_at:desc')
        sort_field, _, direction = sort_by.partition(':')
        rows.sort(key=lambda t: t[sort_field] or '', reverse=direction == 'desc')

        per_page = min(int(params.get('per_page', 100)), 100)
        page = int(params.get('page', 1))
        total_pages = max(1, -(-len(rows) // per_page))
        start = (page - 1) * per_page
        return MockResponse(200, json.dumps({
            'transactions': rows[start:start + per_page],
            'meta': {
                'current_page': page,
                'next_page': page + 1 if page < total_pages else None,
                'prev_page': page - 1 if page > 1 else None,
                'total_pages': total_pages,
                'total_count': len(rows),
                'per_page': per_page,
            },
        }))


class FinTSFixtureTransport(FixtureTransport):
    """A deterministic python-fints client factory backed by redacted fixtures."""

    def __init__(self) -> None:
        super().__init__()
        self.data = json.loads(
            (BANK_FIXTURES_DIR / 'fints' / 'accounts.json').read_text(encoding='utf8'),
        )
        self.product_ids: list[str] = []
        self.restored_client_data: list[bytes | None] = []
        self.init_tan_response: Any = None

    def __call__(self, *args: Any, **kwargs: Any) -> FinTSFixtureTransport:
        if (product_id := kwargs.get('product_id')) is not None:
            self.product_ids.append(product_id)
        self.restored_client_data.append(kwargs.get('from_data'))
        return self

    def __enter__(self) -> None:
        return None

    def __exit__(self, *_args: object) -> None:
        return None

    def deconstruct(self, including_private: bool = False) -> bytes:
        return b'fixture-client-state-private' if including_private else b'fixture-client-state'

    def _raise_forced(self) -> None:
        if self.forced_response is None:
            return
        if self.forced_response.status_code in (401, 403):
            raise FinTSClientPINError('credentials rejected')
        if self.forced_response.status_code >= 500:
            raise FinTSConnectionError('endpoint unavailable')

    def get_sepa_accounts(self) -> list[SEPAAccount]:
        self.requests.append(('accounts', {}))
        self._raise_forced()
        return [SEPAAccount(
            row['iban'], row['bic'], row['accountnumber'], row['subaccount'], row['blz'],
        ) for row in self.data['accounts']]

    def get_balance(self, account: SEPAAccount) -> SimpleNamespace:
        self.requests.append(('balance', {'account': account.iban}))
        self._raise_forced()
        row = next(row for row in self.data['accounts'] if row['iban'] == account.iban)
        return SimpleNamespace(amount=SimpleNamespace(
            amount=FVal(row['balance']),
            currency=row['currency'],
        ))

    def get_transactions(
            self,
            account: SEPAAccount,
            start_date=None,
            end_date=None,
            include_pending: bool = False,
    ) -> list[SimpleNamespace]:
        params = {
            'account': account.iban,
            'end_date': end_date,
            'include_pending': include_pending,
        }
        if start_date is not None:
            params['start_date'] = start_date
        self.requests.append(('transactions', params))
        self._raise_forced()
        return [SimpleNamespace(data={
            **row,
            'date': datetime.fromisoformat(row['date']).date(),
            'amount': SimpleNamespace(amount=FVal(row['amount']), currency=row['currency']),
        }) for row in self.data['transactions'] if start_date is None or datetime.fromisoformat(row['date']).date() >= start_date]  # noqa: E501


@dataclass
class BankConnectorKit:
    location: LocationIdentifier
    connector_class: type[BankConnector]
    create_transport: Callable[[], FixtureTransport]
    expected_balances: dict[Any, FVal]  # asset -> amount the fixtures add up to
    expected_event_count: int  # final transactions in the fixtures
    cursor_param: str  # the request parameter an incremental sync must carry
    per_page_param: str | None = 'per_page'
    page_param: str = 'page'
    small_page_size: int = 5  # a page size that forces pagination over the fixtures
    extra_ctor_kwargs: dict[str, Any] = field(default_factory=dict)
    credential_values: dict[str, str] = field(default_factory=lambda: {
        'api_key': 'test-login',
        'api_secret': 'test-secret',
    })

    def create(self, database: DBHandler, msg_aggregator: MessagesAggregator) -> BankConnector:
        credentials = self.connector_class.api_credentials_from_values(
            name=f'{self.location!s}1',
            location=self.location,
            values=self.credential_values,
        )
        assert credentials.api_secret is not None
        return self.connector_class(
            name=credentials.name,
            api_key=credentials.api_key,
            secret=credentials.api_secret,
            database=database,
            msg_aggregator=msg_aggregator,
            **self.extra_ctor_kwargs,
        )


def _qonto_expected_balance() -> FVal:
    data = json.loads((BANK_FIXTURES_DIR / 'qonto' / 'organization.json').read_text(encoding='utf8'))  # noqa: E501
    return sum(
        (FVal(a['balance_cents']) / 100 for a in data['organization']['bank_accounts'] if a['status'] == 'active'),  # noqa: E501
        start=FVal(0),
    )


BANK_KITS: list[BankConnectorKit] = [
    BankConnectorKit(
        location=LOCATION_QONTO,
        connector_class=Qonto,
        create_transport=QontoFixtureTransport,
        expected_balances={A_EUR: _qonto_expected_balance()},
        expected_event_count=28,
        cursor_param='updated_at_from',
    ),
    BankConnectorKit(
        location=FINTS_CONNECTOR,
        connector_class=Fints,
        create_transport=FinTSFixtureTransport,
        expected_balances={A_EUR: FVal('1250')},
        expected_event_count=3,
        cursor_param='start_date',
        per_page_param=None,
        extra_ctor_kwargs={'product_id': '0123456789012345678901234'},
        credential_values={
            'bank_code': '12030000',
            'endpoint': 'https://bank.example/fints',
            'username': 'test-login',
            'pin': 'test-secret',
        },
    ),
]


def patch_bank_transport(connector: BankConnector, transport: FixtureTransport) -> _patch:
    if isinstance(connector, Fints):
        return patch.object(connector, 'client_factory', transport)
    return patch.object(connector.session, 'get', side_effect=transport)
