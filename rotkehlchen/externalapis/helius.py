import logging
from http import HTTPStatus
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal

import gevent
import requests
from base58 import b58decode

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.chain.solana.types import SolanaInstruction, SolanaTransaction
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.db.solanatx import DBSolanaTx
from rotkehlchen.errors.misc import MissingAPIKey, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.interface import ExternalService, ExternalServiceWithApiKey
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_int,
    deserialize_solana_address,
    deserialize_timestamp,
    deserialize_tx_signature,
)
from rotkehlchen.utils.misc import get_chunks
from rotkehlchen.utils.serialization import jsonloads_list

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import SolanaAddress

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
                    f'Helius API request {response.url} failed '
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

    def get_transactions(self, signatures: list[str], relevant_address: 'SolanaAddress') -> None:
        """Query Helius for txs corresponding to the given signatures and save them in the DB.
        May raise:
        - RemoteError if there was a problem with the remote query.
        - MissingAPIKey if the user has no Helius api key.
        """
        solana_tx_db = DBSolanaTx(database=self.db)
        for chunk in get_chunks(signatures, MAX_TX_BATCH_SIZE):
            txs, token_accounts_mappings = [], {}
            for raw_tx in self._query(endpoint='transactions', params={'transactions': chunk}):
                try:
                    tx, token_accounts_mapping = self._deserialize_raw_tx(raw_tx)
                    txs.append(tx)
                    token_accounts_mappings.update(token_accounts_mapping)
                except DeserializationError as e:
                    log.error(e)  # the error from _deserialize_raw_tx is already descriptive.

            if len(txs) == 0:
                continue  # don't try to save if none of the txs were deserialized

            # Save each chunk as it is queried to avoid losing progress if something goes wrong.
            with self.db.conn.write_ctx() as write_cursor:
                solana_tx_db.add_transactions(
                    write_cursor=write_cursor,
                    solana_transactions=txs,
                    relevant_address=relevant_address,
                )
                solana_tx_db.add_token_account_mappings(
                    write_cursor=write_cursor,
                    token_accounts_mappings=token_accounts_mappings,
                )

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
        - TypeError if the accounts are not iterable or an address is not a string
        - DeserializationError if there is an invalid address
        """
        try:
            data = b58decode(raw_instruction['data'])
        except AttributeError as e:  # b58decode raises this if the value is not a string
            raise DeserializationError(f'Invalid instruction data type: {e!s}') from e

        return SolanaInstruction(
            execution_index=execution_index,
            parent_execution_index=parent_execution_index,
            program_id=deserialize_solana_address(raw_instruction['programId']),
            data=data,
            accounts=[deserialize_solana_address(x) for x in raw_instruction['accounts']],
        )

    def _deserialize_raw_tx(self, raw_tx: dict[str, Any]) -> tuple[SolanaTransaction, dict['SolanaAddress', tuple['SolanaAddress', 'SolanaAddress']]]:  # noqa: E501
        """Deserialize a raw transaction from Helius to a SolanaTransaction.
        Returns a tuple containing the transaction
        and a mapping of token accounts to (owner, mint).

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

            token_account_mapping = {}
            for entry in raw_tx.get('tokenTransfers', []):
                token_account_mapping[deserialize_solana_address(entry['fromTokenAccount'])] = (
                    deserialize_solana_address(entry['fromUserAccount']),
                    deserialize_solana_address(entry['mint']),
                )
                token_account_mapping[deserialize_solana_address(entry['toTokenAccount'])] = (
                    deserialize_solana_address(entry['toUserAccount']),
                    deserialize_solana_address(entry['mint']),
                )

            return (SolanaTransaction(
                fee=deserialize_int(value=raw_tx['fee'], location='solana tx fee from helius'),
                slot=deserialize_int(value=raw_tx['slot'], location='solana tx slot from helius'),
                success=raw_tx.get('transactionError') is None,
                signature=deserialize_tx_signature(raw_tx['signature']),
                block_time=deserialize_timestamp(raw_tx['timestamp']),
                account_keys=[deserialize_solana_address(x['account']) for x in raw_tx['accountData']],  # noqa: E501
                instructions=instructions,
            ), token_account_mapping)
        except (KeyError, ValueError, TypeError, DeserializationError) as e:
            msg = f'Missing key {e!s}' if isinstance(e, KeyError) else str(e)
            raise DeserializationError(f'Failed to deserialize Helius raw tx due to {msg}') from e
