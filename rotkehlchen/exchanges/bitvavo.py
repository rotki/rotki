import logging
import urllib.parse
from collections import defaultdict
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal

import requests

from rotkehlchen.api.websockets.typedefs import UserMessageRecord
from rotkehlchen.assets.converters import asset_from_bitvavo
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.exchanges.utils import SignatureGeneratorMixin
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import ApiKey, ApiSecret, ExchangeAuthCredentials, Location, Timestamp
from rotkehlchen.user_messages import BadData
from rotkehlchen.utils.misc import ts_now_in_ms
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.data_structures import MarginPosition
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

BITVAVO_BASE_URL: Final = 'https://api.bitvavo.com/v2'
BITVAVO_API_PATH_PREFIX: Final = '/v2'
BITVAVO_KEY_HEADER: Final = 'Bitvavo-Access-Key'
BITVAVO_TIMESTAMP_HEADER: Final = 'Bitvavo-Access-Timestamp'
BITVAVO_SIGNATURE_HEADER: Final = 'Bitvavo-Access-Signature'
BitvavoEndpoint = Literal['/balance']


class Bitvavo(ExchangeInterface, SignatureGeneratorMixin):
    """Bitvavo exchange API docs: https://docs.bitvavo.com/docs/rest-api/introduction/

    Authenticated requests carry the API key, a millisecond timestamp and an HMAC-SHA256
    signature of ``timestamp + method + path + body`` in the request headers, where the
    path includes the ``/v2`` prefix and the query string, and the body is empty for GET.

    The "Read-only" key permission is enough.
    """

    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
    ):
        super().__init__(
            name=name,
            location=Location.BITVAVO,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.base_uri = BITVAVO_BASE_URL
        self.session.headers.update({BITVAVO_KEY_HEADER: self.api_key})

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if changed is True:
            self.session.headers.update({BITVAVO_KEY_HEADER: self.api_key})

        return changed

    def first_connection(self) -> None:
        self.first_connection_made = True

    def _generate_signature(
            self,
            method: Literal['GET', 'POST'],
            request_path: str,
            timestamp: str,
            body: str = '',
    ) -> str:
        return self.generate_hmac_signature(message=f'{timestamp}{method}{request_path}{body}')

    def _api_query(
            self,
            endpoint: BitvavoEndpoint,
            options: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Request a Bitvavo API endpoint and return the decoded JSON body.

        Bitvavo answers errors with a non-2xx status and a body of the form
        ``{"errorCode": 305, "error": "Your API key is not active."}``.

        May raise RemoteError.
        """
        options = options or {}
        request_path = f'{BITVAVO_API_PATH_PREFIX}{endpoint}'
        if len(query_string := urllib.parse.urlencode(options)) != 0:
            request_path = f'{request_path}?{query_string}'

        request_url = f'{self.base_uri}{endpoint}'
        log.debug('Bitvavo API request', request_url=request_url, options=options)
        try:
            response = self.session.get(
                url=request_url,
                params=options,
                headers={  # the api key is always present in the session headers
                    BITVAVO_TIMESTAMP_HEADER: (timestamp := str(ts_now_in_ms())),
                    BITVAVO_SIGNATURE_HEADER: self._generate_signature(
                        method='GET',
                        request_path=request_path,
                        timestamp=timestamp,
                    ),
                },
                timeout=CachedSettings().get_timeout_tuple(),
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Bitvavo request at {request_url} connection error: {e!s}.') from e

        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            raise RemoteError(
                f'Bitvavo request at {request_url} failed due to rate limiting. '
                f'Bitvavo blocks the key or IP for a minute after the weight limit is exceeded.',
            )

        try:
            response_data = response.json()
        except JSONDecodeError as e:
            raise RemoteError(
                f'Bitvavo request at {request_url} returned invalid JSON with '
                f'HTTP status {response.status_code}: {response.text}',
            ) from e

        if response.status_code != HTTPStatus.OK:
            if isinstance(response_data, dict) and 'errorCode' in response_data:
                raise RemoteError(
                    f'Bitvavo request at {request_url} failed with error code '
                    f'{response_data["errorCode"]}: {response_data.get("error")}',
                )
            raise RemoteError(
                f'Bitvavo request at {request_url} responded with HTTP status '
                f'{response.status_code}: {response.text}',
            )

        return response_data

    def validate_api_key(self) -> tuple[bool, str]:
        """Validates that the Bitvavo API key can read account balances."""
        try:
            self._api_query(endpoint='/balance')
        except RemoteError as e:
            return False, str(e)
        return True, ''

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        """Query the spot balances of the account.

        Each entry splits the balance into what is free (``available``) and what is
        reserved by open orders (``inOrder``). Both belong to the user, so they are summed.
        """
        try:
            balances = self._api_query(endpoint='/balance')
        except RemoteError as e:
            log.error('Failed to query Bitvavo balances due to %s', e)
            return None, f'Failed to query Bitvavo balances due to a remote error: {e!s}'

        if not isinstance(balances, list):
            msg = f'Bitvavo balance query returned unexpected data: {balances}'
            log.error(msg)
            return None, msg

        amounts: defaultdict[AssetWithOracles, FVal] = defaultdict(FVal)
        for balance in balances:
            try:
                amount = (
                    deserialize_fval(balance['available']) +
                    deserialize_fval(balance['inOrder'])
                )
                if amount == ZERO:
                    continue

                asset = asset_from_bitvavo(balance['symbol'])
            except (DeserializationError, KeyError) as e:
                log.error('Failed to deserialize Bitvavo balance %s. %s', balance, e)
                self.add_classified_error(
                    'Failed to deserialize a Bitvavo balance entry. '
                    'Check logs for details. Ignoring it.',
                    BadData(record=UserMessageRecord.BALANCE, error=str(e)),
                )
                continue
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='balance query',
                )
                continue

            amounts[asset] += amount

        return dict(self.balances_from_amounts(amounts)), ''

    def query_online_margin_history(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> list[MarginPosition]:
        """Bitvavo has no margin trading."""
        return []
