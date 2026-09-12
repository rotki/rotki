"""Test kit for bank connectors.

A kit is everything the framework-level contract tests need to run a connector against its
committed, redacted fixtures: how to build it, a transport serving the fixtures the way the
bank's API would, and the numbers the fixtures are expected to produce.
"""
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import _patch, patch
from urllib.parse import urlparse

from rotkehlchen.banks.qonto import Qonto
from rotkehlchen.constants.assets import A_EUR
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import ApiKey, ApiSecret, Location

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.banks.connector import BankConnector
    from rotkehlchen.db.dbhandler import DBHandler
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

    def __call__(self, url: str, params: dict[str, Any] | None = None, **kwargs: Any) -> MockResponse:  # noqa: E501
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
        page = int(params.get('current_page', 1))
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


@dataclass
class BankConnectorKit:
    location: Location
    connector_class: type[BankConnector]
    create_transport: Callable[[], FixtureTransport]
    expected_balances: dict[Any, FVal]  # asset -> amount the fixtures add up to
    expected_event_count: int  # final transactions in the fixtures
    cursor_param: str  # the request parameter an incremental sync must carry
    per_page_param: str = 'per_page'
    small_page_size: int = 5  # a page size that forces pagination over the fixtures
    extra_ctor_kwargs: dict[str, Any] = field(default_factory=dict)

    def create(self, database: DBHandler, msg_aggregator: MessagesAggregator) -> BankConnector:
        return self.connector_class(
            name=f'{self.location!s}1',
            api_key=ApiKey('test-login'),
            secret=ApiSecret(b'test-secret'),
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
        location=Location.QONTO,
        connector_class=Qonto,
        create_transport=QontoFixtureTransport,
        expected_balances={A_EUR: _qonto_expected_balance()},
        expected_event_count=28,
        cursor_param='updated_at_from',
    ),
]


def patch_bank_transport(connector: BankConnector, transport: FixtureTransport) -> _patch:
    return patch.object(connector.session, 'get', side_effect=transport)
