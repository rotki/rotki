"""Bookkeeping of erc20 tokens whose details have to be queried again.

When the details of a token can't be fully queried while it is first seen, the token is
marked in the global DB unique cache by chain and address. The mark keeps the details that
were saved in the token, so that a retry can tell if a user edit or an asset update changed
them in the meantime, and how many retries found the details still incomplete.

If the token could not be created at all, the transactions where it was seen are recorded in
the user DB so they can be redecoded once the token exists. When the details of an existing
token change, all the transactions with its events are recorded too, since the amounts of the
events were calculated with the old decimals.
"""
import logging
from json import JSONDecodeError
from typing import TYPE_CHECKING, Final, Literal, NamedTuple

from rotkehlchen.db.constants import TOKENRETRYTXPREFIX
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import (
    compute_cache_key,
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    CacheType,
    ChainID,
    ChecksumEvmAddress,
    EVMTxHash,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.serialization import jsonloads_dict, rlk_jsondumps

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# retries that can find the details incomplete before the token is left as it is
TOKEN_DETAILS_RETRY_MAX_ATTEMPTS: Final = 5


class TokenDetailsRetryMark(NamedTuple):
    chain_id: ChainID
    address: ChecksumEvmAddress
    attempts: int
    # (name, symbol, decimals) saved in the token when marked. None if it was not created.
    saved: tuple[str, str | None, int] | None


class TokenRetryTx(NamedTuple):
    key: str
    chain_id: ChainID
    address: ChecksumEvmAddress
    tx_hash: EVMTxHash


def _mark_key_parts(
        chain_id: ChainID,
        address: ChecksumEvmAddress,
) -> tuple[Literal[CacheType.TOKEN_DETAILS_RETRY], str, str]:
    return CacheType.TOKEN_DETAILS_RETRY, str(chain_id.serialize_for_db()), address


def _serialize_mark(attempts: int, saved: tuple[str, str | None, int] | None) -> str:
    return rlk_jsondumps({'attempts': attempts, 'saved': saved})


def mark_token_details_retry(
        chain_id: ChainID,
        address: ChecksumEvmAddress,
        saved: tuple[str, str | None, int] | None,
) -> None:
    """Mark a token to have its details queried again. A token that was already marked
    keeps its attempts, so seeing it again does not make it retry forever."""
    key_parts = _mark_key_parts(chain_id=chain_id, address=address)
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        attempts = 0
        if (value := globaldb_get_unique_cache_value(write_cursor, key_parts)) is not None:
            try:
                attempts = jsonloads_dict(value)['attempts']
            except (JSONDecodeError, KeyError) as e:
                log.error('Malformed token details retry mark %s due to %s', value, e)

        globaldb_set_unique_cache_value(
            write_cursor=write_cursor,
            key_parts=key_parts,
            value=_serialize_mark(attempts=attempts, saved=saved),
        )


def get_token_details_retry_marks(
        chain_id: ChainID,
        limit: int,
) -> list[TokenDetailsRetryMark]:
    """Get up to limit marked tokens of the chain, the least recently tried first"""
    prefix = compute_cache_key((CacheType.TOKEN_DETAILS_RETRY, str(chain_id.serialize_for_db())))
    marks = []
    with GlobalDBHandler().conn.read_ctx() as cursor:
        for key, value in cursor.execute(
            # the 0x makes sure that the chain id is not the prefix of a longer one
            "SELECT key, value FROM unique_cache WHERE key LIKE ? ESCAPE '\\' "
            'ORDER BY last_queried_ts, key LIMIT ?',
            (prefix.replace('_', '\\_') + '0x%', limit),
        ):
            try:
                data = jsonloads_dict(value)
                marks.append(TokenDetailsRetryMark(
                    chain_id=chain_id,
                    address=ChecksumEvmAddress(key[len(prefix):]),
                    attempts=data['attempts'],
                    saved=None if (saved := data['saved']) is None else tuple(saved),
                ))
            except (JSONDecodeError, KeyError) as e:
                log.error('Skipping malformed token details retry mark %s due to %s', key, e)

    return marks


def remove_token_details_retry_mark(chain_id: ChainID, address: ChecksumEvmAddress) -> None:
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'DELETE FROM unique_cache WHERE key=?',
            (compute_cache_key(_mark_key_parts(chain_id=chain_id, address=address)),),
        )


def count_token_details_retry_attempt(
        database: DBHandler,
        mark: TokenDetailsRetryMark,
) -> None:
    """Count a retry that found the details incomplete. When the attempts run out the token
    is left as it is, together with the transactions waiting for it."""
    if (attempts := mark.attempts + 1) >= TOKEN_DETAILS_RETRY_MAX_ATTEMPTS:
        log.warning(
            'Giving up on querying the details of token %s at %s after %d attempts',
            mark.address, mark.chain_id.to_name(), attempts,
        )
        remove_token_details_retry_mark(chain_id=mark.chain_id, address=mark.address)
        with database.conn.write_ctx() as write_cursor:
            write_cursor.execute(
                "DELETE FROM key_value_cache WHERE name LIKE ? ESCAPE '\\'",
                (f'{_tx_key_prefix(chain_id=mark.chain_id, address=mark.address)}\\_%',),
            )
        return

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_unique_cache_value(  # also moves it to the back of the queue
            write_cursor=write_cursor,
            key_parts=_mark_key_parts(chain_id=mark.chain_id, address=mark.address),
            value=_serialize_mark(attempts=attempts, saved=mark.saved),
        )


def _tx_key_prefix(chain_id: ChainID, address: ChecksumEvmAddress) -> str:
    return f'{TOKENRETRYTXPREFIX}_{chain_id.serialize_for_db()}_{address}'


def record_token_retry_tx(
        database: DBHandler,
        chain_id: ChainID,
        address: ChecksumEvmAddress,
        tx_hash: EVMTxHash,
) -> None:
    """Record a transaction to redecode once the token at the given address exists"""
    with database.conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'INSERT OR REPLACE INTO key_value_cache(name, value) VALUES(?, ?)',
            (f'{_tx_key_prefix(chain_id=chain_id, address=address)}_{tx_hash!s}', str(tx_hash)),
        )


def record_token_retry_txs_of_asset(
        database: DBHandler,
        chain_id: ChainID,
        address: ChecksumEvmAddress,
        identifier: str,
) -> None:
    """Record for redecoding all the transactions with events of the token. Used when the
    details of a token change, since the amounts of its events used the old decimals."""
    with database.conn.write_ctx() as write_cursor:
        tx_hashes = [deserialize_evm_tx_hash(row[0]) for row in write_cursor.execute(
            'SELECT DISTINCT chain_events_info.tx_ref FROM history_events INNER JOIN '
            'chain_events_info ON history_events.identifier=chain_events_info.identifier '
            'WHERE history_events.asset=?',
            (identifier,),
        ).fetchall()]  # materialized since the same cursor writes next
        write_cursor.executemany(
            'INSERT OR REPLACE INTO key_value_cache(name, value) VALUES(?, ?)',
            [
                (f'{_tx_key_prefix(chain_id=chain_id, address=address)}_{tx_hash!s}', str(tx_hash))
                for tx_hash in tx_hashes
            ],
        )


def get_token_retry_txs(cursor: DBCursor) -> list[TokenRetryTx]:
    """Get the recorded transactions to redecode"""
    txs = []
    for key, value in cursor.execute(
        "SELECT name, value FROM key_value_cache WHERE name LIKE ? ESCAPE '\\'",
        (f'{TOKENRETRYTXPREFIX}\\_%',),
    ):
        try:
            _, chain_id, address, _ = key.split('_')
            txs.append(TokenRetryTx(
                key=key,
                chain_id=ChainID.deserialize_from_db(int(chain_id)),
                address=ChecksumEvmAddress(address),
                tx_hash=deserialize_evm_tx_hash(value),
            ))
        except (ValueError, DeserializationError) as e:
            log.error('Skipping malformed token retry transaction %s due to %s', key, e)

    return txs


def delete_token_retry_txs(write_cursor: DBCursor, keys: list[str]) -> None:
    write_cursor.executemany(
        'DELETE FROM key_value_cache WHERE name=?',
        [(key,) for key in keys],
    )
