"""Bookkeeping of erc20 tokens whose details have to be queried again.

When the details of a token can't be fully queried while it is first seen, the token is
marked in the global DB unique cache by chain and address. The mark keeps the details that
were saved in the token and which of them are only defaults or fallbacks, so that a retry fills
only those and can tell if something else, like a decoder or an asset update, filled them in the
meantime. It also keeps how many retries found the details still incomplete. When the
attempts run out the mark is moved to a given up key, so the token keeps whatever it has and
is never retried again, even if it is seen again. A given up token that could not be created
keeps its attempts in the given up mark until the token is added, so that the transactions
where it was seen are still redecoded then. Tokens the user edited or added are given up with
no attempts.

When the details of an existing token change, the transactions with its events are flagged for
redecoding, since their amounts were calculated with the old decimals. A token that could not be
created at all gets the transactions with logs of its contract flagged once it is created.
"""
import logging
from json import JSONDecodeError
from typing import TYPE_CHECKING, Final, Literal, NamedTuple

from rotkehlchen.chain.evm.constants import ERC20_PROPERTIES
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.globaldb.cache import (
    compute_cache_key,
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
    globaldb_update_cache_last_ts,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    CacheType,
    ChainID,
    ChecksumEvmAddress,
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
# (name, symbol, decimals) of a token as saved in the global DB
TokenDetails = tuple[str | None, str | None, int]
# index of each of the ERC20_PROPERTIES in TokenDetails
TOKEN_DETAILS_INDEX: Final = {'name': 0, 'symbol': 1, 'decimals': 2}


class TokenDetailsRetryMark(NamedTuple):
    chain_id: ChainID
    address: ChecksumEvmAddress
    attempts: int
    # (name, symbol, decimals) saved in the token when marked. None if it was not created.
    saved: TokenDetails | None
    # the ERC20_PROPERTIES whose saved values are not the ones of the chain
    missing: frozenset[str] = frozenset(ERC20_PROPERTIES)


def _mark_key_parts(
        chain_id: ChainID,
        address: ChecksumEvmAddress,
        given_up: bool = False,
) -> tuple[Literal[CacheType.TOKEN_DETAILS_RETRY, CacheType.TOKEN_DETAILS_GIVEN_UP], str, str]:
    return (
        CacheType.TOKEN_DETAILS_GIVEN_UP if given_up else CacheType.TOKEN_DETAILS_RETRY,
        str(chain_id.serialize_for_db()),
        address,
    )


def _is_given_up(cursor: DBCursor, chain_id: ChainID, address: ChecksumEvmAddress) -> bool:
    return globaldb_get_unique_cache_value(
        cursor=cursor,
        key_parts=_mark_key_parts(chain_id=chain_id, address=address, given_up=True),
    ) is not None


def is_token_details_retry_given_up(chain_id: ChainID, address: ChecksumEvmAddress) -> bool:
    """Whether the details of the token are never queried again, because its attempts ran
    out or the user edited or added it"""
    with GlobalDBHandler().conn.read_ctx() as cursor:
        return _is_given_up(cursor=cursor, chain_id=chain_id, address=address)


def _serialize_mark(
        attempts: int,
        saved: TokenDetails | None,
        missing: frozenset[str] = frozenset(ERC20_PROPERTIES),
) -> str:
    return rlk_jsondumps({'attempts': attempts, 'saved': saved, 'missing': sorted(missing)})


def mark_token_details_retry(
        chain_id: ChainID,
        address: ChecksumEvmAddress,
        saved: TokenDetails | None,
        missing: frozenset[str] = frozenset(ERC20_PROPERTIES),
) -> None:
    """Mark a token to have its details queried again. A token that was already marked
    keeps its attempts and one whose attempts ran out is not marked again, so seeing it
    again does not make it retry forever. missing are the ERC20_PROPERTIES whose saved
    values are only defaults or fallbacks."""
    key_parts = _mark_key_parts(chain_id=chain_id, address=address)
    value = _serialize_mark(attempts=0, saved=saved, missing=missing)
    # this runs for every sighting of the token while decoding, so only write when needed
    with GlobalDBHandler().conn.read_ctx() as cursor:
        if _is_given_up(cursor=cursor, chain_id=chain_id, address=address):
            return

        existing = globaldb_get_unique_cache_value(cursor=cursor, key_parts=key_parts)

    if existing is not None:
        try:
            data = jsonloads_dict(existing)
            if (
                data.get('saved') == (None if saved is None else list(saved)) and
                data.get('missing') == sorted(missing)
            ):
                return  # already marked as it is now. Keep its place in the queue

            value = _serialize_mark(attempts=data['attempts'], saved=saved, missing=missing)
        except (JSONDecodeError, KeyError) as e:
            log.error('Malformed token details retry mark %s due to %s', existing, e)

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        if _is_given_up(cursor=write_cursor, chain_id=chain_id, address=address):
            return  # given up since it was read

        globaldb_set_unique_cache_value(
            write_cursor=write_cursor,
            key_parts=key_parts,
            value=value,
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
                    # marks from before the missing details were kept had all of them retried
                    missing=frozenset(data.get('missing', ERC20_PROPERTIES)),
                ))
            except (JSONDecodeError, KeyError) as e:
                log.error('Skipping malformed token details retry mark %s due to %s', key, e)

    return marks


def _delete_mark(write_cursor: DBCursor, chain_id: ChainID, address: ChecksumEvmAddress) -> bool:
    """Delete the retry mark of a token. Returns whether it was marked."""
    write_cursor.execute(
        'DELETE FROM unique_cache WHERE key=?',
        (compute_cache_key(_mark_key_parts(chain_id=chain_id, address=address)),),
    )
    return write_cursor.rowcount != 0


def remove_token_details_retry_mark(chain_id: ChainID, address: ChecksumEvmAddress) -> None:
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        _delete_mark(write_cursor=write_cursor, chain_id=chain_id, address=address)


def stop_token_details_retry(chain_id: ChainID, address: ChecksumEvmAddress) -> bool:
    """Never query again the details of a token, since the user edited them. The token is
    moved to the given up key, which also keeps it out of the tokens picked for having their
    identifier as name.

    Returns whether the token was marked to be retried, which means its events may have
    amounts calculated with details that were not the right ones.
    """
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        was_marked = _delete_mark(write_cursor=write_cursor, chain_id=chain_id, address=address)
        globaldb_set_unique_cache_value(
            write_cursor=write_cursor,
            key_parts=_mark_key_parts(chain_id=chain_id, address=address, given_up=True),
            value=_serialize_mark(attempts=0, saved=None),
        )

    return was_marked


def postpone_token_details_retry(marks: list[TokenDetailsRetryMark]) -> None:
    """Move marks to the back of the queue without counting an attempt, so that tokens whose
    query failed while the nodes seemed down don't stay in front of the rest"""
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        for mark in marks:
            globaldb_update_cache_last_ts(
                write_cursor=write_cursor,
                cache_type=CacheType.TOKEN_DETAILS_RETRY,
                key_parts=(str(mark.chain_id.serialize_for_db()), mark.address),
            )


def count_token_details_retry_attempt(mark: TokenDetailsRetryMark) -> None:
    """Count a retry that found the details incomplete, creating the mark if the token was
    not marked. When the attempts run out the mark is moved to the given up key: the token
    keeps whatever it has and is not retried again."""
    attempts = mark.attempts + 1
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        if _is_given_up(cursor=write_cursor, chain_id=mark.chain_id, address=mark.address):
            return  # the user edited it while it was queried

        if given_up := attempts >= TOKEN_DETAILS_RETRY_MAX_ATTEMPTS:
            log.warning(
                'Giving up on querying the details of token %s at %s after %d attempts',
                mark.address, mark.chain_id.to_name(), attempts,
            )
            _delete_mark(write_cursor=write_cursor, chain_id=mark.chain_id, address=mark.address)

        globaldb_set_unique_cache_value(  # also moves it to the back of the queue
            write_cursor=write_cursor,
            key_parts=_mark_key_parts(
                chain_id=mark.chain_id,
                address=mark.address,
                given_up=given_up,
            ),
            value=_serialize_mark(attempts=attempts, saved=mark.saved, missing=mark.missing),
        )


def pop_given_up_tokens_added_since(chain_id: ChainID) -> list[ChecksumEvmAddress]:
    """Return the tokens of the chain that were given up before they could be created and
    exist now, for example after an asset update. Their attempts are cleared so that each one
    is returned only once."""
    with GlobalDBHandler().conn.read_ctx() as cursor:  # not under the write lock, rarely finds any
        addresses = [row[0] for row in cursor.execute(
            'SELECT B.address FROM evm_tokens AS B JOIN unique_cache AS U '
            'ON U.key=? || B.chain || B.address WHERE B.chain=? '
            "AND json_extract(U.value, '$.saved') IS NULL "
            "AND json_extract(U.value, '$.attempts') > 0",
            (CacheType.TOKEN_DETAILS_GIVEN_UP.serialize(), chain_id.serialize_for_db()),
        )]
    if len(addresses) == 0:
        return addresses

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        for address in addresses:
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=_mark_key_parts(chain_id=chain_id, address=address, given_up=True),
                value=_serialize_mark(attempts=0, saved=None),
            )

    return addresses


def redecode_token_txs(
        database: DBHandler,
        chain_id: ChainID,
        address: ChecksumEvmAddress,
        created: bool = False,
) -> None:
    """Flag for redecoding the transactions with events of the token, since their amounts
    were calculated with details that the token does not have anymore. If the token was just
    created there are no events of it, so the transactions with logs of its contract are
    flagged instead, to decode the events that were skipped for lack of the token."""
    from rotkehlchen.db.evmtx import DBEvmTx  # avoid circular import
    query, value = (
        (
            'evmtx_receipt_logs AS L JOIN evm_transactions AS E ON E.identifier=L.tx_id '
            'WHERE E.chain_id=? AND L.address=?'
        ),
        address,
    ) if created else (
        (
            'history_events AS H JOIN chain_events_info AS C ON H.identifier=C.identifier '
            'JOIN evm_transactions AS E ON E.tx_hash=C.tx_ref WHERE E.chain_id=? AND H.asset=?'
        ),
        evm_address_to_identifier(address=address, chain_id=chain_id),
    )

    with database.conn.read_ctx() as cursor:  # the logs query is slow. Not under the write lock
        transactions = {
            tx_id: deserialize_evm_tx_hash(tx_hash) for tx_id, tx_hash in cursor.execute(
                f'SELECT DISTINCT E.identifier, E.tx_hash FROM {query}',
                (chain_id.serialize_for_db(), value),
            )
        }
    with database.conn.write_ctx() as write_cursor:
        DBEvmTx(database).flag_transactions_for_redecoding(
            write_cursor=write_cursor,
            transactions=transactions,
            chain_id=chain_id,  # type: ignore[arg-type]  # only chains with transactions have any
        )
