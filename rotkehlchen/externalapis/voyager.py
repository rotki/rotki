import logging
from http import HTTPStatus
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final

import gevent
import requests

from rotkehlchen.chain.starknet.types import StarknetTransaction
from rotkehlchen.chain.starknet.utils import normalize_starknet_address
from rotkehlchen.errors.misc import MissingAPIKey, RemoteError
from rotkehlchen.externalapis.interface import (
    ExternalService,
    ExternalServiceWithRecommendedApiKey,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import StarknetAddress, Timestamp
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

VOYAGER_API_URL: Final = 'https://api.voyager.online/beta'
DEFAULT_PAGE_SIZE: Final = 100

# Rate limit retry settings — Voyager allows 5 req/s on free tier
BACKOFF_SECONDS: Final = 1
RETRY_LIMIT: Final = 2


class Voyager(ExternalServiceWithRecommendedApiKey):

    def __init__(self, database: 'DBHandler') -> None:
        super().__init__(database=database, service_name=ExternalService.VOYAGER)

    def _query(
            self,
            endpoint: str,
            params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Queries the Voyager API with the given endpoint and params.

        May raise:
        - MissingAPIKey if the user has no Voyager api key.
        - RemoteError if there was a problem with the remote query.
        """
        if (api_key := self._get_api_key()) is None:
            raise MissingAPIKey('Voyager API key is missing')

        retry_count = 0
        while True:
            log.debug(f'Querying Voyager: {VOYAGER_API_URL}/{endpoint}')
            try:
                response = requests.get(
                    url=f'{VOYAGER_API_URL}/{endpoint}',
                    params=params,
                    headers={'x-api-key': api_key},
                    timeout=(30, 30),
                )
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'Voyager API request failed due to {e!s}') from e

            if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                if retry_count >= RETRY_LIMIT:
                    raise RemoteError('Getting Voyager too many requests error even after retrying.')  # noqa: E501

                log.debug(f'Got too many requests error from Voyager. Will backoff for {BACKOFF_SECONDS} second.')  # noqa: E501
                gevent.sleep(BACKOFF_SECONDS)
                retry_count += 1
                continue

            if response.status_code != HTTPStatus.OK:
                raise RemoteError(
                    f'Voyager API request {response.url} failed '
                    f'with HTTP status code {response.status_code} and text '
                    f'{response.text}',
                )

            break

        try:
            json_ret = jsonloads_dict(response.text)
        except JSONDecodeError as e:
            raise RemoteError(
                f'Voyager API request {response.url} returned invalid '
                f'JSON response: {response.text}',
            ) from e

        return json_ret

    def get_tx_hashes_for_address(self, address: str) -> list[str]:
        """Fetch all transaction hashes for a Starknet address via Voyager txns endpoint.

        Uses GET /beta/txns?to={address} which returns all transactions where
        the given address is the contract/account. Paginates through all pages.

        May raise:
        - MissingAPIKey if the user has no Voyager api key.
        - RemoteError if there was a problem with the remote query.
        """
        tx_hashes: list[str] = []
        page = 1

        while True:
            result = self._query(
                endpoint='txns',
                params={
                    'to': address,
                    'p': page,
                    'ps': DEFAULT_PAGE_SIZE,
                },
            )

            items = result.get('items', [])
            if not items:
                break

            for tx in items:
                tx_hash = tx.get('hash')
                if tx_hash:
                    tx_hashes.append(tx_hash)

            # Check if we've fetched all pages
            last_page = result.get('lastPage', page)
            if page >= last_page:
                break

            page += 1

        log.debug(f'Voyager discovered {len(tx_hashes)} tx hashes for {address}')
        return tx_hashes

    def get_transaction(self, tx_hash: str) -> dict[str, Any]:
        """Fetch enriched transaction details from Voyager.

        May raise:
        - MissingAPIKey if the user has no Voyager api key.
        - RemoteError if there was a problem with the remote query.
        """
        return self._query(endpoint=f'txns/{tx_hash}')

    def get_transactions_for_address(self, address: str) -> list[StarknetTransaction]:
        """Fetch all transactions for a Starknet address with full details from Voyager.

        Uses the txns list endpoint (which includes basic details like actualFee,
        timestamp, etc.) and then fetches full details only when needed.

        May raise:
        - MissingAPIKey if the user has no Voyager api key.
        - RemoteError if there was a problem with the remote query.
        """
        transactions: list[StarknetTransaction] = []
        page = 1

        while True:
            result = self._query(
                endpoint='txns',
                params={
                    'to': address,
                    'p': page,
                    'ps': DEFAULT_PAGE_SIZE,
                },
            )

            items = result.get('items', [])
            if not items:
                break

            for item in items:
                tx = self._deserialize_voyager_tx(item)
                if tx is not None:
                    transactions.append(tx)

            last_page = result.get('lastPage', page)
            if page >= last_page:
                break

            page += 1

        log.debug(f'Voyager fetched {len(transactions)} transactions for {address}')
        return transactions

    def get_transaction_object(self, tx_hash: str) -> StarknetTransaction:
        """Fetch a transaction from Voyager and return as StarknetTransaction.

        May raise:
        - MissingAPIKey if the user has no Voyager api key.
        - RemoteError if there was a problem with the remote query.
        """
        raw = self.get_transaction(tx_hash)
        tx = self._deserialize_voyager_tx(raw)
        if tx is None:
            raise RemoteError(f'Failed to deserialize Voyager transaction {tx_hash}')
        return tx

    @staticmethod
    def _deserialize_voyager_tx(raw: dict[str, Any]) -> StarknetTransaction | None:
        """Convert a Voyager transaction response into a StarknetTransaction.

        Works with both list endpoint items and single-tx endpoint responses.
        """
        try:
            tx_hash = raw['hash']
            sender = raw.get('senderAddress') or raw.get('contractAddress', '0x0')
            from_address = StarknetAddress(normalize_starknet_address(sender))
            contract = raw.get('contractAddress')
            to_address = StarknetAddress(
                normalize_starknet_address(contract),
            ) if contract else None

            actual_fee = int(raw.get('actualFee', '0'))
            timestamp = Timestamp(raw.get('timestamp', 0))
            block_number = raw.get('blockNumber', 0)
            tx_type = raw.get('type', 'INVOKE')

            # Parse maxFee — Voyager may return hex string or int
            max_fee_raw = raw.get('maxFee', '0')
            if isinstance(max_fee_raw, str) and max_fee_raw.startswith('0x'):
                max_fee = int(max_fee_raw, 16)
            else:
                max_fee = int(max_fee_raw)

            # Determine status
            status = raw.get('status', 'ACCEPTED_ON_L2')
            execution = raw.get('executionStatus', 'Succeeded')
            if execution != 'Succeeded':
                status = execution

            return StarknetTransaction(
                transaction_hash=tx_hash,
                block_number=block_number,
                block_timestamp=timestamp,
                from_address=from_address,
                to_address=to_address,
                selector=raw.get('selector'),
                calldata=raw.get('calldata', []),
                max_fee=max_fee,
                actual_fee=actual_fee,
                status=status,
                transaction_type=tx_type,
            )
        except (KeyError, ValueError, TypeError) as e:
            log.error(f'Failed to deserialize Voyager tx {raw.get("hash", "?")} due to {e!s}')
            return None
