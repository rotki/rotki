import logging
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, Literal

import requests

from rotkehlchen.chain.gnosis.modules.gnosis_pay.constants import CPT_GNOSIS_PAY
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import EVMTxHash, Location, Timestamp, deserialize_evm_tx_hash
from rotkehlchen.utils.misc import set_user_agent, timestamp_to_iso8601
from rotkehlchen.utils.serialization import jsonloads_list

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GnosisPay:
    """This is the gnosis pay API interface

    https://api.gnosispay.com/api-docs/

    For now they have no api keys but you can get the __Secure-authjs.session-token
    cookie from your local storage once logged in and put it to rotki. Then all data
    is queriable.
    """

    def __init__(self, database: 'DBHandler', session_token: str) -> None:
        self.database = database
        self.session = requests.session()
        self.session_token = session_token
        set_user_agent(self.session)

    def _query(
            self,
            endpoint: Literal['transactions'],
            params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Query a gnosis pay API endpoint with the hacky session token authentication"""
        querystr = 'https://app.gnosispay.com/api/v1/' + endpoint
        log.debug(f'Querying Gnosis PAy API  {querystr}')
        timeout = CachedSettings().get_timeout_tuple()
        try:
            response = self.session.get(
                url=querystr,
                params=params,
                timeout=timeout,
                cookies={'__Secure-authjs.session-token': self.session_token},
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Querying {querystr} failed due to {e!s}') from e

        if response.status_code != 200:
            raise RemoteError(
                f'Gnosis Pay API request {response.url} failed '
                f'with HTTP status code {response.status_code} and text '
                f'{response.text}',
            )

        try:
            json_ret = jsonloads_list(response.text)
        except JSONDecodeError as e:
            raise RemoteError(
                f'Gnosis Pay API returned invalid JSON response: {response.text}',
            ) from e

        return json_ret

    def get_and_process_transactions(
            self,
            after_ts: Timestamp,
            tx_hash: EVMTxHash | None = None,
    ) -> None:
        """Query for gnosis pay transactions and merchant data after a given timestamp.

        Then search for our events and if there is a matching event overlay the
        merchant data on top.

                DMed by gnosis pay devs
                export enum PaymentStatus {
                  Approved = "Approved",
                  IncorrectPin = "IncorrectPin",
                  InsufficientFunds = "InsufficientFunds",
                  InvalidAmount = "InvalidAmount",
                  PinEntryTriesExceeded = "PinEntryTriesExceeded",
                  IncorrectSecurityCode = "IncorrectSecurityCode",
                  Reversal = "Reversal",
                  PartialReversal = "PartialReversal",
                  Other = "Other",
                }

        mcc is the merchant code category and details can be seen here:
        https://usa.visa.com/content/dam/VCOM/download/merchants/visa-merchant-data-standards-manual.pdf
        """
        data = self._query(
            endpoint='transactions',
            params={'after': timestamp_to_iso8601(after_ts)},
        )
        dbevents = DBHistoryEvents(self.database)
        for entry in data:
            try:
                if entry['status'] != 'Approved':
                    continue  # only check approved

                entry_tx_hash = deserialize_evm_tx_hash(entry['transactions'][0]['hash'])  # take 1st transaction for now  # noqa: E501
                if tx_hash and tx_hash != entry_tx_hash:
                    continue

                # now get the corresponding event
                with self.database.conn.read_ctx() as cursor:
                    events = dbevents.get_history_events(
                        cursor=cursor,
                        filter_query=EvmEventFilterQuery.make(
                            tx_hashes=[entry_tx_hash],
                            counterparties=[CPT_GNOSIS_PAY],
                            location=Location.GNOSIS,
                        ),
                        has_premium=True,
                    )

                if len(events) != 1:
                    log.error(f'Could not find gnosis pay event corresponding to {entry_tx_hash.hex()} in the DB. Skipping.')  # pylint: disable=no-member # noqa: E501
                    continue

                verb, preposition = 'Pay', 'to'
                if int(entry['mcc']) == 6011:  # ATM cash withdrawal
                    verb, preposition = 'Withdraw', 'from'

                tx_currency_symbol = entry['transactionCurrency']['symbol']
                billing_currency_symbol = entry['billingCurrency']['symbol']
                tx_currency_amount = FVal(entry['transactionAmount']) / FVal(10 ** entry['transactionCurrency']['decimals'])  # noqa: E501
                merchant_name = entry['merchant']['name'].rstrip()
                notes = f'{verb} {tx_currency_amount} {tx_currency_symbol}'
                if tx_currency_symbol != billing_currency_symbol:
                    billing_currency_amount = FVal(entry['billingAmount']) / FVal(10 ** entry['billingCurrency']['decimals'])  # noqa: E501
                    notes += f' ({billing_currency_amount} {billing_currency_symbol})'

                notes += f' {preposition} {merchant_name}'
                city = entry['merchant']['city'].rstrip()
                if not (city.startswith('+') or city.isdigit()):  # for some reason sometiems there is phone numbers in merchant data instead of a city name  # noqa: E501
                    notes += f' in {city}'

                notes += f' :country:{entry["merchant"]["country"]["alpha2"]}:'
                querystr = 'UPDATE history_events SET notes=? WHERE identifier=?'
                bindings = (notes, events[0].identifier)
                log.debug(f'Updating notes for gnosis pay event with tx_hash={entry_tx_hash.hex()}')  # pylint: disable=no-member # noqa: E501
                with self.database.user_write() as write_cursor:
                    write_cursor.execute(querystr, bindings)

            except KeyError as e:
                log.error(f'Could not find key {e!s} in Gnosis pay transaction response: {entry}')
                continue


def init_gnosis_pay(database: 'DBHandler') -> GnosisPay | None:
    """Create a gnosis pay instance using the provided database"""
    with database.conn.read_ctx() as cursor:
        result = cursor.execute(
            'SELECT api_key FROM external_service_credentials WHERE name=?',
            ('gnosis_pay',),
        ).fetchone()
        if result is None:
            return None

    return GnosisPay(database=database, session_token=result[0])
