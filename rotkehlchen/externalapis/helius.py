import logging
from http import HTTPStatus
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal

import gevent
import requests
from base58 import b58decode
from solders.solders import Signature

from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.chain.solana.types import SolanaInstruction, SolanaTransaction
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.db.solanatx import DBSolanaTx
from rotkehlchen.errors.misc import MissingAPIKey, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.interface import (
    ExternalService,
    ExternalServiceWithRecommendedApiKey,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_int,
    deserialize_solana_address,
    deserialize_timestamp,
    deserialize_tx_signature,
)
from rotkehlchen.types import SupportedBlockchain
from rotkehlchen.utils.misc import get_chunks
from rotkehlchen.utils.serialization import jsonloads_list

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import SolanaAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

HELIUS_API_URL: Final = 'https://api.helius.xyz/v0'
HELIUS_RPC_URL: Final = 'https://mainnet.helius-rpc.com'

# Max allowed by the api
# https://www.helius.dev/docs/api-reference/enhanced-transactions/gettransactions#body-transactions
MAX_TX_BATCH_SIZE: Final = 100

# The rate limit is 2 requests per second for txs on the free plan, so if backing off for a second
# does not fix it, then the user has likely consumed all their api credits for the month.
# https://www.helius.dev/docs/billing/plans-and-rate-limits#historical-data
BACKOFF_SECONDS: Final = 1
RETRY_LIMIT: Final = 1


class Helius(ExternalServiceWithRecommendedApiKey):

    def __init__(self, database: 'DBHandler') -> None:
        super().__init__(database=database, service_name=ExternalService.HELIUS)

    def _query(
            self,
            endpoint: Literal['transactions'],
            params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Queries the Helius API with the given endpoint and params.
        May raise RemoteError if there was a problem with the remote query.
        """
        if (api_key := self._get_api_key()) is None:
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

    def maybe_get_rpc_node(self) -> WeightedNode | None:
        """Returns the Helius RPC node if the user has an api key."""
        if (api_key := self._get_api_key()) is None:
            return None

        return WeightedNode(
            node_info=NodeName(
                name='Helius',
                endpoint=f'{HELIUS_RPC_URL}?api-key={api_key}',
                blockchain=SupportedBlockchain.SOLANA,
                owned=False,
            ),
            weight=ONE,
            active=True,
        )

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

    def _deserialize_token_account_mappings(
            self,
            signature: Signature,
            raw_transfers: list[dict[str, Any]] | None,
    ) -> dict['SolanaAddress', tuple['SolanaAddress', 'SolanaAddress']]:
        """Deserialize raw token transfers from Helius into token account mappings.
        Since a missing mapping doesn't break the entire tx, any errors in this process are
        caught and logged to avoid breaking the deserialization of the entire tx.
        """
        token_account_mapping: dict[SolanaAddress, tuple[SolanaAddress, SolanaAddress]] = {}
        if raw_transfers is None:
            return token_account_mapping

        for entry in raw_transfers:
            try:
                mint = deserialize_solana_address(entry['mint'])
            except (DeserializationError, KeyError) as e:
                msg = f'Missing key {e!s}' if isinstance(e, KeyError) else str(e)
                log.error(
                    f'Encountered Helius token transfer entry with invalid mint {entry} '
                    f'in {signature} due to {msg}. Skipping.',
                )
                continue

            for token_account_key, user_account_key in (
                    ('fromTokenAccount', 'fromUserAccount'),
                    ('toTokenAccount', 'toUserAccount'),
            ):
                if not (
                    (raw_token_account := entry.get(token_account_key)) and
                    (raw_user_account := entry.get(user_account_key))
                ):  # These can be empty in some cases. For example, Helius has a transfer entry
                    # for the `Mint To` instruction which has no `from` values.
                    continue  # so continue without error

                try:
                    token_account_mapping[deserialize_solana_address(raw_token_account)] = (
                        deserialize_solana_address(raw_user_account),
                        mint,
                    )
                except DeserializationError as e:
                    log.warning(
                        'Failed to load token account owner/mint mapping from Helius '
                        f'token transfer entry {entry} in {signature} due to {e!s}. Skipping.',
                    )

        return token_account_mapping

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

            return (SolanaTransaction(
                fee=deserialize_int(value=raw_tx['fee'], location='solana tx fee from helius'),
                slot=deserialize_int(value=raw_tx['slot'], location='solana tx slot from helius'),
                success=raw_tx.get('transactionError') is None,
                signature=(signature := deserialize_tx_signature(raw_tx['signature'])),
                block_time=deserialize_timestamp(raw_tx['timestamp']),
                account_keys=[deserialize_solana_address(x['account']) for x in raw_tx['accountData']],  # noqa: E501
                instructions=instructions,
            ), self._deserialize_token_account_mappings(
                signature=signature,
                raw_transfers=raw_tx.get('tokenTransfers'),
            ))
        except (KeyError, ValueError, TypeError, DeserializationError) as e:
            msg = f'Missing key {e!s}' if isinstance(e, KeyError) else str(e)
            raise DeserializationError(
                f'Failed to deserialize Helius raw tx with signature '
                f'{raw_tx.get("signature", "Unknown")} due to {msg}. Raw tx data: {raw_tx}',
            ) from e
