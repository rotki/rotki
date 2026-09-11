"""Qonto bank connector (Tier 1, official Business API).

Facts this connector relies on, verified against a live organization in the spike of
rotki issue #13052:

- Auth is the API key: ``Authorization: <login>:<secret key>``, colon joined, no Base64.
  Read endpoints need no strong customer authentication; payment endpoints are OAuth-only
  and out of reach, so this connector is read-only by construction.
- ``/v2/organization`` embeds the bank accounts with settled (``balance``) and authorized
  balances, in ``_cents`` integers next to floats. The cents are the source of truth.
- ``/v2/transactions`` needs a ``bank_account_id`` selector, paginates with
  ``current_page``/``per_page`` (capped at 100 silently) and a ``meta.next_page`` that is
  null on the last page. Unknown query parameter names are silently ignored, unknown
  ``status[]``/``sort_by`` values are HTTP 400.
- ``amount`` is always positive, direction is ``side`` (credit/debit). ``settled_balance``
  is the running balance after the transaction; the sum of signed completed amounts equals
  the account balance exactly.
- The default listing returns only ``completed`` transactions. ``declined`` ones are
  only listed when asked for and never moved money; ``pending``/``reversed`` were not
  observable. Only ``completed`` is ingested.
- ``updated_at`` is a real last-modified timestamp (verified: editing a note bumped it and
  nothing else), so it drives the incremental cursor via ``updated_at_from``.
- Counterparty details sit under a sub-object named after ``operation_type``
  (``transfer``/``income``); the display name is ``label``, the reference ``reference``.
"""
import logging
from datetime import UTC, datetime
from http import HTTPStatus
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final

import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.banks.connector import BankConnector
from rotkehlchen.banks.errors import BankAuthExpired, BankRateLimited, BankSchemaDrift
from rotkehlchen.banks.manifests import QONTO_MANIFEST
from rotkehlchen.banks.normalization import (
    BankAccount,
    BankTransaction,
    BankTransactionKind,
    BankTransactionSide,
)
from rotkehlchen.concurrency import cancellable_sleep
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import iso8601ts_to_timestamp, ts_sec_to_ms
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import ApiKey, ApiSecret, ExchangeAuthCredentials, Timestamp
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

QONTO_API_URL: Final = 'https://thirdparty.qonto.com/v2'
PER_PAGE: Final = 100
FINAL_STATUS: Final = 'completed'
KNOWN_STATUSES: Final = frozenset({'completed', 'pending', 'declined', 'reversed'})
OPERATION_TYPE_TO_KIND: Final = {
    'transfer': BankTransactionKind.TRANSFER,
    'income': BankTransactionKind.TRANSFER,
    'swift_income': BankTransactionKind.TRANSFER,
    'direct_debit': BankTransactionKind.DIRECT_DEBIT,
    'card': BankTransactionKind.CARD,
    'qonto_fee': BankTransactionKind.FEE,
    'cheque': BankTransactionKind.OTHER,
    'recall': BankTransactionKind.OTHER,
    'refund': BankTransactionKind.OTHER,
}


class Qonto(BankConnector):
    manifest = QONTO_MANIFEST

    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            name=name,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self._reported_drift: set[str] = set()
        self._set_auth_header()

    def _set_auth_header(self) -> None:
        self.session.headers.update({
            'Authorization': f'{self.api_key}:{self.secret.decode()}',
            'Accept': 'application/json',
        })

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if changed:
            self._set_auth_header()
        return changed

    # ---- transport ----

    def _api_query(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET an endpoint and map the response onto the framework errors.

        May raise BankAuthExpired, BankRateLimited, BankSchemaDrift or RemoteError.
        """
        url = f'{QONTO_API_URL}/{endpoint}'
        retries_left = CachedSettings().get_query_retry_limit()
        timeout = CachedSettings().get_timeout_tuple()
        while True:
            log.debug('Qonto API query', endpoint=endpoint, params=params)
            try:
                response = self.session.get(url, params=params, timeout=timeout)
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'Qonto API request to {endpoint} failed due to {e!s}') from e

            if response.status_code != HTTPStatus.TOO_MANY_REQUESTS:
                break

            retry_after_header = response.headers.get('Retry-After')
            retry_after = float(retry_after_header) if retry_after_header else None
            retries_left -= 1
            if retries_left <= 0:
                raise BankRateLimited(
                    f'Qonto rate limited the {endpoint} query',
                    retry_after=retry_after,
                )
            wait = retry_after if retry_after is not None else 2.0 ** (3 - retries_left)
            log.debug('Got a 429 from Qonto %s. Backing off for %s seconds', endpoint, wait)
            cancellable_sleep(wait)

        if response.status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            raise BankAuthExpired(
                f'Qonto returned HTTP {response.status_code} for {endpoint}. '
                f'The login/secret key pair is wrong or was revoked.',
            )
        if response.status_code != HTTPStatus.OK:
            raise RemoteError(
                f'Qonto query {endpoint} failed with HTTP {response.status_code}: '
                f'{response.text[:200]}',
            )
        try:
            return jsonloads_dict(response.text)
        except JSONDecodeError as e:
            raise BankSchemaDrift(
                'Qonto returned a non-JSON or non-object body',
                context={'endpoint': endpoint, 'status': response.status_code},
            ) from e

    def _report_drift_once(self, field: str, value: str) -> None:
        """Warn the user once per unknown enum value and keep going. Enum values carry
        no account data so they can be shown verbatim."""
        if (key := f'{field}:{value}') in self._reported_drift:
            return
        self._reported_drift.add(key)
        log.warning('Qonto %s returned unknown %s value %s', self.name, field, value)
        self.msg_aggregator.add_warning(
            f'Qonto returned an unknown transaction {field} "{value}" for {self.name}. '
            f'Transactions with it are skipped until rotki learns about it. '
            f'Please report this so the connector can be updated.',
        )

    # ---- deserialization ----

    def _resolve_fiat(self, symbol: str) -> AssetWithOracles | None:
        try:
            return Asset(symbol).resolve_to_fiat_asset()
        except (UnknownAsset, WrongAssetType):
            self.send_unknown_asset_message(
                asset_identifier=symbol,
                details='Qonto bank account currency',
            )
            return None

    def _deserialize_account(self, entry: dict[str, Any]) -> BankAccount | None:
        try:
            asset = self._resolve_fiat(entry['currency'])
            if asset is None:
                return None
            return BankAccount(
                identifier=entry['id'],
                name=entry.get('name') or entry.get('slug') or entry['id'],
                asset=asset,
                balance=FVal(entry['balance_cents']) / 100,
                iban=entry.get('iban'),
                is_active=entry.get('status') == 'active',
            )
        except (KeyError, TypeError, ValueError) as e:
            raise BankSchemaDrift(
                f'Qonto bank account entry could not be read: {e!s}',
                context={'endpoint': 'organization', 'keys': sorted(entry)},
            ) from e

    def _deserialize_transaction(
            self,
            entry: dict[str, Any],
            account: BankAccount,
    ) -> BankTransaction | None:
        """Return the normalized transaction, or None when it is not final or not ours to
        ingest. Raises BankSchemaDrift when the payload shape is not the known one."""
        try:
            if (status := entry['status']) != FINAL_STATUS:
                if status not in KNOWN_STATUSES:
                    self._report_drift_once('status', str(status))
                return None

            operation_type = entry['operation_type']
            kind = OPERATION_TYPE_TO_KIND.get(operation_type)
            if kind is None:
                self._report_drift_once('operation_type', str(operation_type))
                kind = BankTransactionKind.OTHER

            side_value = entry['side']
            if side_value == 'credit':
                side = BankTransactionSide.CREDIT
            elif side_value == 'debit':
                side = BankTransactionSide.DEBIT
            else:
                raise DeserializationError(f'unknown side {side_value}')

            asset = account.asset
            if (currency := entry['currency']) != account.asset.identifier:
                if (resolved := self._resolve_fiat(currency)) is None:
                    return None
                asset = resolved

            counterparty = entry.get(operation_type)
            counterparty_account = None
            if isinstance(counterparty, dict):
                counterparty_account = counterparty.get('counterparty_account_number')

            return BankTransaction(
                source_id=entry['id'],
                account_id=entry['bank_account_id'],
                timestamp=ts_sec_to_ms(iso8601ts_to_timestamp(entry['settled_at'])),
                asset=asset,
                amount=FVal(entry['amount_cents']) / 100,
                side=side,
                kind=kind,
                counterparty_name=entry.get('clean_counterparty_name') or entry.get('label'),
                counterparty_account=counterparty_account,
                reference=entry.get('reference') or None,
                updated_at=iso8601ts_to_timestamp(entry['updated_at']),
            )
        except (KeyError, TypeError, ValueError, DeserializationError) as e:
            raise BankSchemaDrift(
                f'Qonto transaction entry could not be read: {e!s}',
                context={'endpoint': 'transactions', 'keys': sorted(entry)},
            ) from e

    # ---- connector interface ----

    def query_accounts(self) -> list[BankAccount]:
        data = self._api_query('organization')
        try:
            entries = data['organization']['bank_accounts']
        except (KeyError, TypeError) as e:
            raise BankSchemaDrift(
                'Qonto organization payload has no bank_accounts',
                context={'endpoint': 'organization', 'keys': sorted(data)},
            ) from e
        if not isinstance(entries, list):
            raise BankSchemaDrift(
                'Qonto bank_accounts is not a list',
                context={'endpoint': 'organization', 'type': type(entries).__name__},
            )

        return [
            account for entry in entries
            if (account := self._deserialize_account(entry)) is not None
        ]

    def query_transactions(
            self,
            account: BankAccount,
            updated_since: Timestamp | None,
    ) -> list[BankTransaction]:
        params: dict[str, Any] = {
            'bank_account_id': account.identifier,
            'status[]': FINAL_STATUS,
            'sort_by': 'updated_at:asc',
            'per_page': PER_PAGE,
            'current_page': 1,
        }
        if updated_since is not None:
            params['updated_at_from'] = datetime.fromtimestamp(updated_since, tz=UTC).strftime('%Y-%m-%dT%H:%M:%SZ')  # noqa: E501

        transactions: list[BankTransaction] = []
        while True:
            data = self._api_query('transactions', params)
            try:
                rows = data['transactions']
                next_page = data['meta']['next_page']
            except (KeyError, TypeError) as e:
                raise BankSchemaDrift(
                    'Qonto transactions payload lacks transactions/meta',
                    context={'endpoint': 'transactions', 'keys': sorted(data)},
                ) from e

            transactions.extend(
                transaction for row in rows
                if (transaction := self._deserialize_transaction(row, account)) is not None
            )

            if next_page is None or len(rows) == 0:
                break
            params['current_page'] = next_page

        return transactions
