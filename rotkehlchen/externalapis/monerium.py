import logging
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal

import requests

from rotkehlchen.chain.evm.decoding.monerium.constants import CPT_MONERIUM
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import EVMTxHash, Location, deserialize_evm_tx_hash
from rotkehlchen.utils.misc import set_user_agent, ts_now
from rotkehlchen.utils.network import create_session
from rotkehlchen.utils.serialization import jsonloads_list

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.evm_event import EvmEvent

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Number of individual tx queries to allow before simply querying all with a single query and
# reprocessing any events that we already have.
MAX_INDIVIDUAL_TX_QUERIES: Final = 4


class Monerium:
    """This is the monerium API interface

    https://monerium.dev/docs/
    https://monerium.dev/docs/getting-started/auth-flow
    """

    def __init__(self, database: 'DBHandler', user: str, password: str) -> None:
        self.database = database
        self.session = create_session()
        self.user = user
        self.password = password
        set_user_agent(self.session)

    def _query(
            self,
            endpoint: Literal['orders'],
            params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Query a monerium API endpoint with basic authentication"""
        querystr = 'https://api.monerium.app/' + endpoint
        log.debug(f'Querying monerium API  {querystr}')
        timeout = CachedSettings().get_timeout_tuple()
        try:
            response = self.session.get(
                url=querystr,
                params=params,
                timeout=timeout,
                auth=(self.user, self.password),
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Querying {querystr} failed due to {e!s}') from e

        if response.status_code != 200:
            raise RemoteError(
                f'Monerium API request {response.url} failed '
                f'with HTTP status code {response.status_code} and text '
                f'{response.text}',
            )

        try:
            json_ret = jsonloads_list(response.text)
        except JSONDecodeError as e:
            raise RemoteError(
                f'Monerium API returned invalid JSON response: {response.text}',
            ) from e

        return json_ret

    def get_and_process_orders(self, tx_hash: EVMTxHash | None = None) -> None:
        """Gets all monerium orders and processes them

        Find all on-chain transactions that match those orders and enrich them appropriately.
        If some of those transactions have not yet been pulled do nothing. Since this
        processing has no pagination and all orders will be pulled again next time this runs.

        This only runs for premium users. The check is on the caller which at
        the moment of writing is the periodic task manager.

        May raise:
        - RemoteError if there is trouble contacting the api
        - KeyError if a key is missing
        - DeserializationError if we fail to deserialize a value
        - DBErrors if we fail to write to the DB

        The way this is currently called all exceptions would kill the task and write
        a stack trace in the logs.

        At the moment monerium has no fees, so this is not processing any fees.
        """
        with self.database.conn.write_ctx() as write_cursor:
            write_cursor.execute(  # remember last time task ran
                'INSERT OR REPLACE INTO key_value_cache (name, value) VALUES (?, ?)',
                (DBCacheStatic.LAST_MONERIUM_QUERY_TS.value, str(ts_now())),
            )

        orders = self._query(
            endpoint='orders',
            params={'txHash': tx_hash.hex()} if tx_hash is not None else None,
        )
        dbevents = DBHistoryEvents(self.database)
        for order in orders:  # orders are returned latest first
            log.debug(f'Processing monerium order {order}')
            if (kind := order['kind']) not in ('redeem', 'issue'):
                log.warning(f'Found order with unexpected {kind=}. Skipping.')
                continue

            tx_hashes = order['txHashes']
            hashes_num = len(tx_hashes)
            counterpart = order['counterpart']
            new_type, new_subtype = None, None
            if hashes_num == 2:  # moving from one chain to another
                new_subtype = HistoryEventSubType.BRIDGE
                if kind == 'redeem':
                    idx = 0
                    suffix = f'to {counterpart["identifier"]["chain"]}'
                    new_type = HistoryEventType.DEPOSIT
                else:  # issue
                    idx = 1
                    suffix = f'from {counterpart["identifier"]["chain"]}'
                    new_type = HistoryEventType.WITHDRAWAL

                tx_hash = deserialize_evm_tx_hash(tx_hashes[idx])
                new_notes = f'Bridge {order["amount"]} EURe {suffix}'
                if (memo := order.get('memo')):
                    new_notes += f' with memo "{memo}"'

            elif hashes_num == 1:
                tx_hash = deserialize_evm_tx_hash(tx_hashes[0])
                if kind == 'redeem':
                    verb = 'Send'
                    preposition = 'to'
                else:  # issue
                    verb = 'Receive'
                    preposition = 'from'

                details = ''
                if (cpt_details := counterpart['details']):
                    name = cpt_details.get('name', '')
                    iban = counterpart.get('identifier', {}).get('iban', '')
                    details = f'{name}'
                    if iban:
                        details += f' ({iban})'

                new_notes = f'{verb} {order["amount"]} EURe via bank transfer {preposition} {details}'  # noqa: E501
                if (memo := order.get('memo')):
                    new_notes += f' with memo "{memo}"'

            else:
                log.warning(f'Found order with unexpected {hashes_num=}. Skipping.')
                continue

            match order['chain']:
                case 'ethereum':
                    location = Location.ETHEREUM
                case 'gnosis':
                    location = Location.GNOSIS
                case 'polygon':
                    location = Location.POLYGON_POS
                case _:
                    log.warning(f'Found order with unexpected chain {order["chain"]}')
                    continue

            # now get the corresponding event
            with self.database.conn.read_ctx() as cursor:
                events = dbevents.get_history_events(
                    cursor=cursor,
                    filter_query=EvmEventFilterQuery.make(
                        tx_hashes=[tx_hash],
                        counterparties=[CPT_MONERIUM],
                        location=location,
                    ),
                    has_premium=True,  # for this function we don't limit anything
                )

            if len(events) != 1:
                log.error(f'Could not find monerium event corresponding to {location!s} {tx_hash.hex()} in the DB. Skipping.')  # pylint: disable=no-member # noqa: E501
                continue

            if self.is_monerium_event_edited(event=(event := events[0])):
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
        """
        tx_hashes = set()
        for event in events:
            if not self.is_monerium_event_edited(event=event):
                tx_hashes.add(event.tx_hash)

        if len(tx_hashes) <= MAX_INDIVIDUAL_TX_QUERIES:
            for tx_hash in tx_hashes:
                self.get_and_process_orders(tx_hash=tx_hash)
        else:  # query all instead if there are too many to query individually
            self.get_and_process_orders()

    @staticmethod
    def is_monerium_event_edited(event: 'EvmEvent') -> bool:
        """Check if an event has already been edited.
        Simply checks whether the notes have been edited to no longer start with Burn or Mint.
        While this is a bit hacky, it avoids needing to save any special state in the DB when
        editing these events.
        """
        return event.notes is not None and not event.notes.startswith(('Burn', 'Mint'))


def init_monerium(database: 'DBHandler') -> Monerium | None:
    """Create a monerium instance using the provided database"""
    with database.conn.read_ctx() as cursor:
        result = cursor.execute(
            'SELECT api_key, api_secret FROM external_service_credentials WHERE name=?',
            ('monerium',),
        ).fetchone()
        if result is None:
            return None

    return Monerium(database=database, user=result[0], password=result[1])
