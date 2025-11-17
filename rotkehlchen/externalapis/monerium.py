import json
import logging
from dataclasses import asdict, dataclass
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal
from urllib.parse import urljoin

import requests
from gevent.lock import Semaphore
from oauthlib.oauth2 import WebApplicationClient

from rotkehlchen.chain.evm.decoding.monerium.constants import CPT_MONERIUM
from rotkehlchen.constants.timing import HOUR_IN_SECONDS
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.api import AuthenticationError
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import EVMTxHash, Location, deserialize_evm_tx_hash
from rotkehlchen.utils.misc import set_user_agent, ts_now
from rotkehlchen.utils.network import create_session
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.evm_event import EvmEvent

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Number of individual tx queries to allow before simply querying all with a single query and
# reprocessing any events that we already have.
MAX_INDIVIDUAL_TX_QUERIES: Final = 4

# TODO move this to env
MONERIUM_API_BASE_URL: Final = 'https://api.monerium.app/'
MONERIUM_ACCEPT_HEADER: Final = 'application/vnd.monerium.api-v2+json'
TOKEN_REFRESH_MARGIN_SECONDS: Final = 60
AUTHORIZATION_CODE_FLOW_CLIENT_ID: Final = '9f93c53a-aa6c-11f0-9078-069e351f134d'
SUPPORTED_MONERIUM_CHAINS: Final = {  # keys are the values used in the monerium's orders endpoint
    'ethereum': Location.ETHEREUM,
    'gnosis': Location.GNOSIS,
    'polygon': Location.POLYGON_POS,
    'arbitrum': Location.ARBITRUM_ONE,
    'scroll': Location.SCROLL,
}


class Monerium:
    """This is the monerium API interface

    https://monerium.dev/docs/
    https://monerium.dev/docs/getting-started/auth-flow
    """

    def __init__(self, database: 'DBHandler') -> None:
        self.database = database
        self.session = create_session()
        set_user_agent(self.session)
        self.oauth_client = MoneriumOAuthClient(database=self.database, session=self.session)

    def _query(
            self,
            endpoint: str,
            params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Query a monerium API endpoint using OAuth authenticated requests.
        May raise:
            - AuthenticationError
            - RemoteError
        """
        if not self.oauth_client.is_authenticated():
            raise AuthenticationError('Monerium not authenticated')

        log.debug(f'Querying monerium API {endpoint}')
        if (response := self.oauth_client.request(
            method='GET',
            endpoint=endpoint,
            params=params,
            timeout=CachedSettings().get_timeout_tuple(),
        )).status_code != 200:
            raise RemoteError(
                f'Monerium API request {response.url} failed with HTTP status code '
                f'{response.status_code} and text {response.text}',
            )

        try:
            return jsonloads_dict(response.text)
        except JSONDecodeError as e:
            raise RemoteError(
                f'Monerium API returned invalid JSON response: {response.text}',
            ) from e

    def get_and_process_orders(self, tx_hash: EVMTxHash | None = None) -> None:
        """Gets all monerium orders and processes them

        Find all on-chain transactions that match those orders and enrich them appropriately.
        If some of those transactions have not yet been pulled do nothing. Since this
        processing has no pagination and all orders will be pulled again next time this runs.

        This only runs for premium users. The check is on the caller which at
        the moment of writing is the periodic task manager.

        May raise:
        - RemoteError if there is trouble contacting the api

        The way this is currently called all exceptions would kill the task and write
        a stack trace in the logs.

        At the moment monerium has no fees, so this is not processing any fees.
        """
        with self.database.conn.write_ctx() as write_cursor:
            write_cursor.execute(  # remember last time task ran
                'INSERT OR REPLACE INTO key_value_cache (name, value) VALUES (?, ?)',
                (DBCacheStatic.LAST_MONERIUM_QUERY_TS.value, str(ts_now())),
            )

        try:
            response = self._query(
                endpoint='orders',
                params={'txHash': str(tx_hash)} if tx_hash is not None else None,
            )
        except AuthenticationError as e:
            log.error(f'Failed to authenticate monerium request due to {e}')
            raise RemoteError('Monerium authentication failed. Check logs for more details') from e

        dbevents = DBHistoryEvents(self.database)
        for order in response['orders']:
            log.debug(f'Processing monerium order {order}')
            if (kind := order['kind']) not in ('redeem', 'issue'):
                log.warning(f'Found order with unexpected {kind=}. Skipping.')
                continue

            try:  # avoid having multiple try/excepts blocks around the logic
                tx_hashes = order['meta']['txHashes']
                counterparty = order['counterpart']
                chain = order['chain']
                amount = order['amount']
                cpt_details = counterparty['details']
            except KeyError as e:
                log.error(f'monerium order response {order} has missing key {e}. Skipping')
                continue

            hashes_num = len(tx_hashes)

            new_type, new_subtype = None, None
            if hashes_num == 2:  # moving from one chain to another
                new_subtype = HistoryEventSubType.BRIDGE
                try:
                    if kind == 'redeem':
                        idx = 0
                        suffix = f'to {counterparty["identifier"]["chain"]}'
                        new_type = HistoryEventType.DEPOSIT
                    else:  # issue
                        idx = 1
                        suffix = f'from {counterparty["identifier"]["chain"]}'
                        new_type = HistoryEventType.WITHDRAWAL
                except KeyError as e:
                    log.error(f'Missing key {e} in monerium order response {order}. Skipping')
                    continue

                tx_hash_raw = tx_hashes[idx]
                new_notes = f'Bridge {amount} EURe {suffix}'
                if (memo := order.get('memo')):
                    new_notes += f' with memo "{memo}"'

            elif hashes_num == 1:
                tx_hash_raw = tx_hashes[0]
                if kind == 'redeem':
                    verb = 'Send'
                    preposition = 'to'
                else:  # issue
                    verb = 'Receive'
                    preposition = 'from'

                details = ''
                if cpt_details:
                    name = cpt_details.get('name', '')
                    iban = counterparty.get('identifier', {}).get('iban', '')
                    details = f'{name}'
                    if iban:
                        details += f' ({iban})'

                new_notes = f'{verb} {amount} EURe via bank transfer {preposition} {details}'
                if (memo := order.get('memo')):
                    new_notes += f' with memo "{memo}"'

            else:
                log.warning(f'Found order with unexpected {hashes_num=}. Skipping.')
                continue

            try:
                tx_hash = deserialize_evm_tx_hash(tx_hash_raw)
            except DeserializationError as e:
                log.error(f'Monerium API returned an invalid tx hash {tx_hash_raw}. Skipping entry {e}')  # noqa: E501
                continue

            if (location := SUPPORTED_MONERIUM_CHAINS.get(chain)) is None:
                log.warning(f'Found order with unexpected chain {chain}')
                continue

            # now get the corresponding event
            with self.database.conn.read_ctx() as cursor:
                events = dbevents.get_history_events_internal(
                    cursor=cursor,
                    filter_query=EvmEventFilterQuery.make(
                        tx_hashes=[tx_hash],
                        counterparties=[CPT_MONERIUM],
                        location=location,
                    ),
                )

            if len(events) != 1:
                log.error(f'Could not find monerium event corresponding to {location!s} {tx_hash!s} in the DB. Skipping.')  # noqa: E501
                continue

            if self.is_monerium_event_edited(event_notes=(event := events[0]).notes):
                continue  # skip if the event is already edited

            querystr = 'UPDATE history_events SET notes=? '
            bindings: list[Any] = [new_notes]
            if new_type:
                querystr = 'UPDATE history_events SET notes=?, type=?, subtype=? '
                bindings.extend([new_type.serialize(), new_subtype.serialize()])  # type: ignore  # both type/subtype are set
            querystr += 'WHERE identifier=?'
            bindings.append(event.identifier)
            with self.database.user_write() as write_cursor:
                write_cursor.execute(querystr, bindings)

    def update_events(self, events: list['EvmEvent']) -> None:
        """Query and update the event txs individually.
        Skips any events that have already been edited.
        Falls back to simply querying all orders if there are too many individual queries.

        May raise:
            - RemoteError if there is trouble contacting the api
        """
        tx_hashes = set()
        for event in events:
            if not self.is_monerium_event_edited(event_notes=event.notes):
                tx_hashes.add(event.tx_ref)

        if len(tx_hashes) <= MAX_INDIVIDUAL_TX_QUERIES:
            for tx_hash in tx_hashes:
                self.get_and_process_orders(tx_hash=tx_hash)
        else:  # query all instead if there are too many to query individually
            self.get_and_process_orders()

    @staticmethod
    def is_monerium_event_edited(event_notes: str | None) -> bool:
        """Check if an event has already been edited.
        Simply checks whether the notes have been edited to no longer start with Burn or Mint.
        While this is a bit hacky, it avoids needing to save any special state in the DB when
        editing these events.
        """
        return event_notes is not None and not event_notes.startswith(('Burn', 'Mint'))


def init_monerium(database: 'DBHandler') -> Monerium | None:
    """Create a monerium instance using the provided database"""
    if not (monerium := Monerium(database=database)).oauth_client.is_authenticated():
        return None

    return monerium


@dataclass
class MoneriumOAuthCredentials:
    access_token: str
    refresh_token: str
    expires_at: int
    user_email: str | None = None
    default_profile_id: str | None = None
    profiles: list[dict[str, Any]] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'MoneriumOAuthCredentials':
        return cls(
            access_token=data['access_token'],
            refresh_token=data['refresh_token'],
            expires_at=int(data['expires_at']),
            user_email=data.get('user_email'),
            default_profile_id=data.get('default_profile_id'),
            profiles=data.get('profiles'),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def is_expiring(self) -> bool:
        return self.expires_at <= ts_now() + TOKEN_REFRESH_MARGIN_SECONDS


class MoneriumOAuthClient:
    """Handles Monerium OAuth token lifecycle and authenticated requests."""

    def __init__(self, database: 'DBHandler', session: requests.Session) -> None:
        """Initialize the OAuth client and preload any cached credentials."""
        self.database = database
        self.session = session
        self.session.headers.setdefault('Accept', MONERIUM_ACCEPT_HEADER)
        self._credentials: MoneriumOAuthCredentials | None = self._load_credentials()
        self._oauth_client: WebApplicationClient | None = None
        self._refresh_lock: Semaphore = Semaphore()
        if self._credentials is not None:
            self._oauth_client = WebApplicationClient(AUTHORIZATION_CODE_FLOW_CLIENT_ID)

    def _load_credentials(self) -> MoneriumOAuthCredentials | None:
        """Load cached OAuth credentials from the database, if any."""
        with self.database.conn.read_ctx() as cursor:
            if (result := self.database.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.MONERIUM_OAUTH_CREDENTIALS,
            )) is None:
                return None

        try:
            raw_data = jsonloads_dict(result)
        except JSONDecodeError as e:
            log.error(f'Failed to parse stored Monerium OAuth credentials: {e!s}')
            return None

        try:
            return MoneriumOAuthCredentials.from_dict(raw_data)
        except KeyError as exc:
            log.error(f'Missing key {exc!s} in stored Monerium OAuth credentials')
            return None

    def _store_credentials(self, credentials: MoneriumOAuthCredentials) -> None:
        """Persist OAuth credentials in the database for future sessions."""
        with self.database.conn.write_ctx() as write_cursor:
            self.database.set_static_cache(
                write_cursor=write_cursor,
                name=DBCacheStatic.MONERIUM_OAUTH_CREDENTIALS,
                value=json.dumps(credentials.to_dict()),
            )

    def clear_credentials(self) -> None:
        """Remove any cached credentials and reset the local OAuth client."""
        with self.database.conn.write_ctx() as write_cursor:
            write_cursor.execute(
                'DELETE FROM key_value_cache WHERE name=?',
                (DBCacheStatic.MONERIUM_OAUTH_CREDENTIALS.value,),
            )

        self._credentials = None
        self._oauth_client = None

    def is_authenticated(self) -> bool:
        """Return True when a valid credential set is loaded."""
        return self._credentials is not None

    def get_status(self) -> dict[str, Any]:
        """Return an authentication status payload for the API."""
        credentials = self._credentials
        if credentials is None:
            return {'authenticated': False}

        return {
            'authenticated': True,
            'user_email': credentials.user_email,
            'default_profile_id': credentials.default_profile_id,
            'profiles': credentials.profiles or [],
            'expires_at': credentials.expires_at,
        }

    def complete_oauth(
            self,
            access_token: str,
            refresh_token: str,
            expires_in: int,
    ) -> dict[str, Any]:
        """Finalize the OAuth handshake and store tokens and user metadata.

        May raise:
        - RemoteError if retrieving the user context fails.
        """
        expires_at = ts_now() + int(expires_in)
        credentials = MoneriumOAuthCredentials(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )

        self._credentials = credentials
        self._oauth_client = WebApplicationClient(AUTHORIZATION_CODE_FLOW_CLIENT_ID)
        self._store_credentials(credentials)

        context = self._fetch_user_context()
        credentials.user_email = context.get('email')
        credentials.default_profile_id = context.get('defaultProfile')
        credentials.profiles = context.get('profiles')
        self._store_credentials(credentials)

        return {
            'success': True,
            'message': 'Successfully authenticated with Monerium',
            'user_email': credentials.user_email,
            'default_profile_id': credentials.default_profile_id,
            'profiles': credentials.profiles or [],
        }

    def ensure_access_token(self) -> None:
        """Refresh the access token when it is close to expiry.

        May raise:
        - AuthenticationError if no credentials are available.
        - RemoteError if refreshing the access token fails.
        """
        if not self.is_authenticated():
            raise AuthenticationError('Monerium not authenticated')

        if not self._credentials.is_expiring():  # type: ignore  # ._credentials is not None because it is checked above
            return

        with self._refresh_lock:
            # ensure that no other greenlet has already refreshed the token
            if not self._credentials.is_expiring():  # type: ignore
                return

            self._refresh_access_token()

    def request(
            self,
            method: Literal['GET', 'POST'],
            endpoint: str,
            params: dict[str, Any] | None = None,
            data: Any | None = None,
            headers: dict[str, str] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> requests.Response:
        """Execute an authenticated request against the Monerium API.

        May raise:
        - AuthenticationError if Monerium is not authenticated.
        - RemoteError if the request fails or the token is rejected.
        """
        self.ensure_access_token()
        credentials = self._credentials
        assert credentials is not None, 'ensure_access_token confirms that it is present and refreshed'  # noqa: E501

        auth_headers = {
            'Authorization': f'Bearer {credentials.access_token}',
            'Accept': MONERIUM_ACCEPT_HEADER,
        }
        if headers:
            auth_headers.update(headers)

        try:
            response = self.session.request(
                method=method,
                url=(url := urljoin(MONERIUM_API_BASE_URL, endpoint)),
                params=params,
                data=data,
                headers=auth_headers,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise RemoteError(f'Querying {url} failed due to {exc!s}') from exc  # pyright: ignore [reportPossiblyUnboundVariable] # url is defined since it is evaluated before the requests call

        if response.status_code == 401:
            # Tokens are invalid, clear stored credentials so user can re-authenticate.
            raise RemoteError('Monerium access token rejected. Please re-authorize.')

        return response

    def _fetch_user_context(self) -> dict[str, Any]:
        """Query the authenticated user context from the Monerium API.

        May raise:
        - RemoteError if the request fails or returns invalid JSON.
        """
        timeout = CachedSettings().get_timeout_tuple()
        response = self.request('GET', 'auth/context', timeout=timeout)

        if response.status_code != 200:
            raise RemoteError(
                f'Failed to query Monerium auth context: {response.status_code} {response.text}',
            )

        try:
            return response.json()
        except requests.RequestException as exc:
            log.error(f'Monerium returned invalid json {response.text}')
            raise RemoteError('Monerium auth context returned invalid JSON') from exc

    def _refresh_access_token(self) -> None:
        """Refresh the stored access token using the refresh token flow.

        May raise:
        - RemoteError if the refresh attempt fails or the response is invalid.
        """
        log.debug('Preparing to refresh monerium oauth token')
        if not self.is_authenticated():
            raise RemoteError('Monerium not authenticated')

        assert self._credentials is not None, 'checked in is_authenticated'
        if self._oauth_client is None:
            self._oauth_client = WebApplicationClient(client_id=AUTHORIZATION_CODE_FLOW_CLIENT_ID)

        try:
            response = self.session.post(
                url=urljoin(MONERIUM_API_BASE_URL, 'auth/token'),
                data={
                    'grant_type': 'refresh_token',
                    'client_id': AUTHORIZATION_CODE_FLOW_CLIENT_ID,
                    'refresh_token': self._credentials.refresh_token,
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=CachedSettings().get_timeout_tuple(),
            )
        except requests.RequestException as exc:
            raise RemoteError(f'Failed to refresh Monerium access token: {exc!s}') from exc

        if response.status_code != 200:
            raise RemoteError(
                f'Failed to refresh Monerium access token: {response.status_code} {response.text}',
            )

        token_response = self._oauth_client.parse_request_body_response(response.text)
        if (access_token := token_response.get('access_token')) is None:
            raise RemoteError('Monerium token refresh did not return an access token')

        refresh_token = token_response.get('refresh_token', self._credentials.refresh_token)
        expires_in_raw = token_response.get('expires_in', HOUR_IN_SECONDS)
        try:
            expires_in = int(expires_in_raw)
        except (TypeError, ValueError) as e:
            raise RemoteError(f'Monerium returned invalid expires_in {expires_in_raw}') from e

        self._credentials.access_token = access_token
        self._credentials.refresh_token = refresh_token
        self._credentials.expires_at = ts_now() + expires_in

        self._store_credentials(self._credentials)
        log.debug('Finished refresh of monerium ouath token')
