import logging
from http import HTTPStatus
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal

import gevent
import requests
from base58 import b58decode
from solders.solders import Signature

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.chain.solana.types import SolanaInstruction, SolanaTransaction
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import MissingAPIKey, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.interface import ExternalService, ExternalServiceWithApiKey
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_int,
    deserialize_solana_address,
    deserialize_timestamp,
)
from rotkehlchen.utils.misc import get_chunks
from rotkehlchen.utils.serialization import jsonloads_list

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

HELIUS_API_URL: Final = 'https://api.helius.xyz/v0'

# Max allowed by the api
# https://www.helius.dev/docs/api-reference/enhanced-transactions/gettransactions#body-transactions
MAX_TX_BATCH_SIZE: Final = 100

# The rate limit is 2 requests per second for txs on the free plan, so if backing off for a second
# does not fix it, then the user has likely consumed all their api credits for the month.
# https://www.helius.dev/docs/billing/plans-and-rate-limits#historical-data
BACKOFF_SECONDS: Final = 1
RETRY_LIMIT: Final = 1


class Helius(ExternalServiceWithApiKey):

    def __init__(self, database: 'DBHandler') -> None:
        super().__init__(database=database, service_name=ExternalService.HELIUS)
        self.warning_given = False

    def _query(
            self,
            endpoint: Literal['transactions'],
            params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Queries the Helius API with the given endpoint and params.
        May raise RemoteError if there was a problem with the remote query.
        """
        if (api_key := self._get_api_key()) is None:
            if not self.warning_given:
                self.db.msg_aggregator.add_message(
                    message_type=WSMessageType.MISSING_API_KEY,
                    data={'service': ExternalService.HELIUS.serialize()},
                )
                self.warning_given = True

            log.warning('Missing Helius api key. Skipping query.')
            raise MissingAPIKey('Helius API key is missing')

        retry_count = 0
        timeout = CachedSettings().get_timeout_tuple()
        while True:
            log.debug(f'Querying Helius: {HELIUS_API_URL}/{endpoint} with params: {params}')
            try:
                response = requests.post(
                    url=f'{HELIUS_API_URL}/{endpoint}/?api-key={api_key}',
                    json=params,
                    timeout=timeout,
                )
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'Helius API request failed due to {e!s}') from e

            if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                if retry_count >= RETRY_LIMIT:
                    raise RemoteError('Getting Helius too many requests error even after retrying.')  # noqa: E501

                log.debug(f'Got too many requests error from Helius. Will backoff for {BACKOFF_SECONDS} second.')  # noqa: E501
                gevent.sleep(BACKOFF_SECONDS)
                retry_count += 1
                continue

            if response.status_code != 200:
                raise RemoteError(
                    f'Etherscan API request {response.url} failed '
                    f'with HTTP status code {response.status_code} and text '
                    f'{response.text}',
                )

            # else status is 200 OK
            break

        try:
            json_ret = jsonloads_list(response.text)
        except JSONDecodeError as e:
            raise RemoteError(
                f'Helius API request {response.url} returned invalid '
                f'JSON response: {response.text}',
            ) from e

        return json_ret

    def _get_raw_transactions(self, signatures: list[str]) -> list[dict[str, Any]] | None:
        """Query Helius for the raw transactions corresponding to the given signatures.
        Returns a list of raw transaction dicts or None if there was a problem querying the API.
        """
        raw_transactions = []
        try:
            for chunk in get_chunks(signatures, MAX_TX_BATCH_SIZE):
                raw_transactions.extend(self._query(
                    endpoint='transactions',
                    params={'transactions': chunk},
                ))
        except (RemoteError, MissingAPIKey) as e:
            log.error(f'Failed to query {len(signatures)} transactions from Helius due to {e!s}')
            return None

        return raw_transactions

    def get_transactions(self, signatures: list[str]) -> list[SolanaTransaction] | None:
        """Query Helius for solana transactions corresponding to the given signatures.
        Returns a list of SolanaTransactions or None if there was a problem querying the API.
        """
        if (raw_transactions := self._get_raw_transactions(signatures)) is None:
            return None

        txs = []
        for raw_tx in raw_transactions:
            try:
                txs.append(self._deserialize_raw_tx(raw_tx))
            except DeserializationError as e:
                log.error(e)
                continue

        return txs

    @staticmethod
    def _deserialize_instruction(
            raw_instruction: dict[str, Any],
            execution_index: int,
            parent_execution_index: int | None = None,
    ) -> SolanaInstruction:
        """Deserialize a raw instruction from Helius to a SolanaInstruction.
        May raise:
        - KeyError
        - ValueError if the data contains invalid base58 characters
        - DeserializationError if there is an invalid address
        """
        return SolanaInstruction(
            execution_index=execution_index,
            parent_execution_index=parent_execution_index,
            program_id=deserialize_solana_address(raw_instruction['programId']),
            data=b58decode(raw_instruction['data']),
            accounts=[deserialize_solana_address(x) for x in raw_instruction['accounts']],
        )

    def _deserialize_raw_tx(self, raw_tx: dict[str, Any]) -> SolanaTransaction:
        """Deserialize a raw transaction from Helius to a SolanaTransaction.
        May raise DeserializationError if there is a problem deserializing.
        """
        try:
            instructions = []
            for idx, instruction in enumerate(raw_tx['instructions']):
                instructions.append(self._deserialize_instruction(
                    raw_instruction=instruction,
                    execution_index=idx,
                ))
                for inner_idx, inner_instruction in enumerate(instruction['innerInstructions']):
                    instructions.append(self._deserialize_instruction(
                        raw_instruction=inner_instruction,
                        execution_index=inner_idx,
                        parent_execution_index=idx,
                    ))

            return SolanaTransaction(
                fee=deserialize_int(value=raw_tx['fee'], location='solana tx fee from helius'),
                slot=deserialize_int(value=raw_tx['slot'], location='solana tx slot from helius'),
                success=raw_tx.get('transactionError') is None,
                signature=Signature.from_string(raw_tx['signature']),
                block_time=deserialize_timestamp(raw_tx['timestamp']),
                account_keys=[deserialize_solana_address(x['account']) for x in raw_tx['accountData']],  # noqa: E501
                instructions=instructions,
            )
        except (KeyError, ValueError, DeserializationError) as e:
            raise DeserializationError(f'Failed to deserialize Helius raw tx due to {e!s}') from e
