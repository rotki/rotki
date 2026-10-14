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
no attempts. A mark of a token that could not be created also keeps the details that the caller
gave, which win over the queried ones when the token is created.

When the details of an existing token change, the transactions with its events are flagged for
redecoding, since their amounts were calculated with the old decimals. A token that could not be
created at all gets the transactions with logs of its contract flagged once it is created.
"""
import logging
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal, NamedTuple

from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.chain.evm.constants import ERC20_PROPERTIES
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.db.utils import get_query_chunks
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
    EVMTxHash,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.serialization import jsonloads_dict, rlk_jsondumps

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

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


TOKEN_DETAILS_QUERY: Final = (
    'SELECT A.name, C.symbol, B.decimals FROM assets AS A JOIN evm_tokens AS B '
    'ON A.identifier=B.identifier LEFT JOIN common_asset_details AS C '
    'ON C.identifier=A.identifier WHERE A.identifier=?'
)


class TokenDetailsRetryMark(NamedTuple):
    chain_id: ChainID
    address: ChecksumEvmAddress
    attempts: int
    # (name, symbol, decimals) saved in the token when marked. None if it was not created.
    saved: TokenDetails | None
    # the ERC20_PROPERTIES whose saved values are not the ones of the chain
    missing: frozenset[str] = frozenset(ERC20_PROPERTIES)
    # details given by the caller of a token that could not be created. They are not queried.
    given: Mapping[str, Any] = {}  # never mutated


class SavedDetails(NamedTuple):
    # the details that were written
    written: frozenset[str]
    # whether the events of the token were calculated with details that changed, so its
    # transactions have to be redecoded and then finish_token_details_retry called
    redecode: bool
    # the details that are still missing and the ones the token has now
    remaining: frozenset[str]
    saved: TokenDetails


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
        given: Mapping[str, Any] | None = None,
) -> str:
    return rlk_jsondumps({
        'attempts': attempts,
        'saved': saved,
        'missing': sorted(missing),
        'given': {} if given is None else dict(given),
    })


def mark_token_details_retry(
        chain_id: ChainID,
        address: ChecksumEvmAddress,
        saved: TokenDetails | None,
        missing: frozenset[str] = frozenset(ERC20_PROPERTIES),
        given: Mapping[str, Any] | None = None,
) -> None:
    """Mark a token to have its details queried again. A token that was already marked
    keeps its attempts and one whose attempts ran out is not marked again, so seeing it
    again does not make it retry forever. missing are the ERC20_PROPERTIES whose saved
    values are only defaults or fallbacks. given are the details that the caller supplied for
    a token that could not be created, to use when it is created. Seeing such a token again
    keeps what the earlier sightings gave, since a later one may not supply any detail."""
    key_parts = _mark_key_parts(chain_id=chain_id, address=address)
    # this runs for every sighting of the token while decoding, so only write when needed
    with GlobalDBHandler().conn.read_ctx() as cursor:
        if _is_given_up(cursor=cursor, chain_id=chain_id, address=address):
            return

        existing = globaldb_get_unique_cache_value(cursor=cursor, key_parts=key_parts)

    attempts = 0
    if existing is not None:
        try:
            data = jsonloads_dict(existing)
            attempts = data['attempts']
            if saved is None and data['saved'] is None:  # still not created
                given = {**data.get('given', {}), **({} if given is None else given)}
                missing = frozenset(ERC20_PROPERTIES) - given.keys()  # the rest is queried

            if (
                data['saved'] == (None if saved is None else list(saved)) and
                data['missing'] == sorted(missing) and
                data.get('given', {}) == ({} if given is None else dict(given))
            ):
                return  # already marked as it is now. Keep its place in the queue
        except (JSONDecodeError, KeyError) as e:
            log.error('Malformed token details retry mark %s due to %s', existing, e)

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        if _is_given_up(cursor=write_cursor, chain_id=chain_id, address=address):
            return  # given up since it was read

        globaldb_set_unique_cache_value(
            write_cursor=write_cursor,
            key_parts=key_parts,
            value=_serialize_mark(attempts=attempts, saved=saved, missing=missing, given=given),
        )


def _deserialize_mark(
        chain_id: ChainID,
        address: ChecksumEvmAddress,
        value: str,
) -> TokenDetailsRetryMark | None:
    try:
        data = jsonloads_dict(value)
        return TokenDetailsRetryMark(
            chain_id=chain_id,
            address=address,
            attempts=data['attempts'],
            saved=None if (saved := data['saved']) is None else tuple(saved),
            # marks from before the missing details were kept had all of them retried
            missing=frozenset(data.get('missing', ERC20_PROPERTIES)),
            given=data.get('given', {}),
        )
    except (JSONDecodeError, KeyError) as e:
        log.error('Skipping malformed token details retry mark %s due to %s', address, e)
        return None


def get_token_details_retry_mark(
        chain_id: ChainID,
        address: ChecksumEvmAddress,
) -> TokenDetailsRetryMark | None:
    """Get the retry mark of a token, if it has one"""
    with GlobalDBHandler().conn.read_ctx() as cursor:
        value = globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=_mark_key_parts(chain_id=chain_id, address=address),
        )

    return None if value is None else _deserialize_mark(chain_id=chain_id, address=address, value=value)  # noqa: E501


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
            if (mark := _deserialize_mark(
                chain_id=chain_id,
                address=ChecksumEvmAddress(key[len(prefix):]),
                value=value,
            )) is not None:
                marks.append(mark)

    return marks


def _delete_mark(write_cursor: DBCursor, chain_id: ChainID, address: ChecksumEvmAddress) -> bool:
    """Delete the retry mark of a token. Returns whether it was marked."""
    write_cursor.execute(
        'DELETE FROM unique_cache WHERE key=?',
        (compute_cache_key(_mark_key_parts(chain_id=chain_id, address=address)),),
    )
    return write_cursor.rowcount != 0


def remove_token_details_retry_mark(
        chain_id: ChainID,
        address: ChecksumEvmAddress,
        only_created: bool = False,
) -> None:
    """Remove the retry mark of a token. With only_created the mark is kept unless it is of a
    token that was not created when marked and exists now, checked in the deletion transaction.
    A mark that is not like that was written after the caller read the one it is cleaning up:
    a decoder created the token with fallbacks, or the token was deleted and seen again, and
    it still tracks what has to be recovered."""
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        if only_created:
            write_cursor.execute(
                "DELETE FROM unique_cache WHERE key=? AND json_extract(value, '$.saved') IS NULL "
                'AND EXISTS (SELECT 1 FROM evm_tokens WHERE identifier=?)',
                (
                    compute_cache_key(_mark_key_parts(chain_id=chain_id, address=address)),
                    evm_address_to_identifier(address=address, chain_id=chain_id),
                ),
            )
        else:
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


def _count_attempt(write_cursor: DBCursor, mark: TokenDetailsRetryMark) -> None:
    """Count a retry that found the details incomplete in the mark, creating it if the token
    was not marked. When the attempts run out the mark is moved to the given up key."""
    attempts = mark.attempts + 1
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
        value=_serialize_mark(
            attempts=attempts,
            saved=mark.saved,
            missing=mark.missing,
            given=mark.given,
        ),
    )


def count_token_details_retry_attempt(mark: TokenDetailsRetryMark) -> None:
    """Count a retry that found the details incomplete, creating the mark if the token was
    not marked. When the attempts run out the mark is moved to the given up key: the token
    keeps whatever it has and is not retried again."""
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        if _is_given_up(cursor=write_cursor, chain_id=mark.chain_id, address=mark.address):
            return  # the user edited it while it was queried

        _count_attempt(write_cursor=write_cursor, mark=mark)


def _read_token_details(write_cursor: DBCursor, identifier: str) -> TokenDetails | None:
    """Read the name, symbol and decimals of a token. None if it does not exist"""
    return write_cursor.execute(TOKEN_DETAILS_QUERY, (identifier,)).fetchone()


def save_found_token_details(
        chain_id: ChainID,
        address: ChecksumEvmAddress,
        mark: TokenDetailsRetryMark | None,
        expected: TokenDetails,
        found: Mapping[str, Any],
) -> SavedDetails | None:
    """Save the queried details of an existing token and update its mark.

    Everything happens in a single global DB write transaction, so a user edit or asset update
    can't land between the checks and the writes: the given up key is checked, the token is
    read and only the details that still have the value they had in expected (the ones of the
    mark, or the ones the token had when selected if it has no mark) are written. The ones
    someone else changed are not needed anymore.

    The events of a token that had details written, or that someone else changed after it was
    marked, were calculated with the old ones. Then the mark is left as it was, or created with
    the old details if there was none, and the caller has to redecode the transactions and call
    finish_token_details_retry. If the process stops in between, the next run finds that the
    token changed and redecodes. Otherwise the mark is removed when no detail is missing anymore,
    and if some are still missing an attempt is counted. The tokens that made progress don't
    count one.

    The caller has to hold the token lock, since a decoder that loaded the token before the
    write would otherwise write it back with its old details.

    Returns what was done, or None if the token was edited by the user or deleted and nothing
    was written.
    """
    needed = frozenset(ERC20_PROPERTIES) if mark is None else mark.missing
    identifier = evm_address_to_identifier(address=address, chain_id=chain_id)
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        if _is_given_up(cursor=write_cursor, chain_id=chain_id, address=address):
            return None  # edited by the user, who has the last word

        if (current := _read_token_details(write_cursor=write_cursor, identifier=identifier)) is None:  # noqa: E501
            _delete_mark(write_cursor=write_cursor, chain_id=chain_id, address=address)
            return None  # deleted

        unchanged = frozenset(
            prop for prop in needed
            if current[TOKEN_DETAILS_INDEX[prop]] == expected[TOKEN_DETAILS_INDEX[prop]]
        )
        written = {prop: found[prop] for prop in unchanged if prop in found}
        for prop, query in (
            ('name', 'UPDATE assets SET name=? WHERE identifier=?'),
            ('symbol', 'UPDATE common_asset_details SET symbol=? WHERE identifier=?'),
            ('decimals', 'UPDATE evm_tokens SET decimals=? WHERE identifier=?'),
        ):
            if prop in written:
                write_cursor.execute(query, (written[prop], identifier))

        remaining = unchanged - written.keys()
        saved = SavedDetails(
            written=frozenset(written),
            redecode=len(written) != 0 or (mark is not None and unchanged != needed),
            remaining=remaining,
            saved=tuple(written.get(prop, current[idx]) for prop, idx in TOKEN_DETAILS_INDEX.items()),  # type: ignore[arg-type]  # name, symbol, decimals  # noqa: E501
        )
        if saved.redecode:
            if mark is None:  # remember the details its events were calculated with
                globaldb_set_unique_cache_value(
                    write_cursor=write_cursor,
                    key_parts=_mark_key_parts(chain_id=chain_id, address=address),
                    value=_serialize_mark(attempts=0, saved=expected, missing=needed),
                )
        elif len(remaining) == 0:
            _delete_mark(write_cursor=write_cursor, chain_id=chain_id, address=address)
        else:
            _count_attempt(write_cursor=write_cursor, mark=TokenDetailsRetryMark(
                chain_id=chain_id,
                address=address,
                attempts=0 if mark is None else mark.attempts,
                saved=saved.saved,
                missing=remaining,
            ))

    AssetResolver.clean_memory_cache(identifier)  # so the token is loaded from the DB
    return saved


def finish_token_details_retry(
        chain_id: ChainID,
        address: ChecksumEvmAddress,
        saved: SavedDetails,
) -> None:
    """Update the mark of a token after its transactions were redecoded, since the events
    now have the details it has: remove it if no detail is missing anymore, or keep only the
    missing ones. Nothing is done if the mark was removed meanwhile or the user edited the
    token."""
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        if _is_given_up(cursor=write_cursor, chain_id=chain_id, address=address):
            return

        key_parts = _mark_key_parts(chain_id=chain_id, address=address)
        if (existing := globaldb_get_unique_cache_value(cursor=write_cursor, key_parts=key_parts)) is None:  # noqa: E501
            return

        if len(saved.remaining) == 0:
            _delete_mark(write_cursor=write_cursor, chain_id=chain_id, address=address)
            return

        try:
            data = jsonloads_dict(existing)
            value = _serialize_mark(
                attempts=data['attempts'],
                saved=saved.saved,
                missing=saved.remaining,
                given=data.get('given'),
            )
        except (JSONDecodeError, KeyError) as e:
            log.error('Malformed token details retry mark %s due to %s', existing, e)
            value = _serialize_mark(attempts=0, saved=saved.saved, missing=saved.remaining)

        globaldb_set_unique_cache_value(write_cursor=write_cursor, key_parts=key_parts, value=value)  # noqa: E501


def get_given_up_tokens_added_since(chain_id: ChainID) -> list[ChecksumEvmAddress]:
    """Return the tokens of the chain that were given up before they could be created and
    exist now, for example after an asset update, and whose transactions have to be redecoded.
    Once that is done their attempts have to be cleared with clear_given_up_attempts, so that
    a crash in between does not lose the redecoding."""
    with GlobalDBHandler().conn.read_ctx() as cursor:  # not under the write lock, rarely finds any
        return [row[0] for row in cursor.execute(
            'SELECT B.address FROM evm_tokens AS B JOIN unique_cache AS U '
            'ON U.key=? || B.chain || B.address WHERE B.chain=? '
            "AND json_extract(U.value, '$.saved') IS NULL "
            "AND json_extract(U.value, '$.attempts') > 0",
            (CacheType.TOKEN_DETAILS_GIVEN_UP.serialize(), chain_id.serialize_for_db()),
        )]


def clear_given_up_attempts(chain_id: ChainID, addresses: Sequence[ChecksumEvmAddress]) -> None:
    """Clear the attempts kept by the given up tokens that were added after being given up.
    Only the entries that still exist are updated, since the token may have been deleted since
    they were selected, which removes them, and a stale cleanup must not recreate one."""
    if len(addresses) == 0:
        return

    value = _serialize_mark(attempts=0, saved=None)
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        write_cursor.executemany(
            'UPDATE unique_cache SET value=? WHERE key=?',
            [
                (value, compute_cache_key(
                    _mark_key_parts(chain_id=chain_id, address=address, given_up=True),
                )) for address in addresses
            ],
        )


def _flag_transactions_for_redecoding(
        database: DBHandler,
        chain_id: ChainID,
        select_query: str,
        values: Sequence[str],
) -> None:
    from rotkehlchen.db.evmtx import DBEvmTx  # avoid circular import
    transactions: dict[int, EVMTxHash] = {}
    with database.conn.read_ctx() as cursor:  # the logs query is slow. Not under the write lock
        for chunk, placeholders in get_query_chunks(data=values):
            transactions |= {
                tx_id: deserialize_evm_tx_hash(tx_hash) for tx_id, tx_hash in cursor.execute(
                    f'SELECT DISTINCT E.identifier, E.tx_hash FROM {select_query % placeholders}',
                    (chain_id.serialize_for_db(), *chunk),
                )
            }
    with database.conn.write_ctx() as write_cursor:
        DBEvmTx(database).flag_transactions_for_redecoding(
            write_cursor=write_cursor,
            transactions=transactions,
            chain_id=chain_id,  # type: ignore[arg-type]  # only chains with transactions have any
        )


def redecode_token_txs(
        database: DBHandler,
        chain_id: ChainID,
        address: ChecksumEvmAddress,
) -> None:
    """Flag for redecoding the transactions with events of the token, since their amounts
    were calculated with details that the token does not have anymore."""
    _flag_transactions_for_redecoding(
        database=database,
        chain_id=chain_id,
        select_query=(
            'history_events AS H JOIN chain_events_info AS C ON H.identifier=C.identifier '
            'JOIN evm_transactions AS E ON E.tx_hash=C.tx_ref WHERE E.chain_id=? AND H.asset IN (%s)'  # noqa: E501
        ),
        values=[evm_address_to_identifier(address=address, chain_id=chain_id)],
    )


def redecode_created_tokens_txs(
        database: DBHandler,
        chain_id: ChainID,
        addresses: Sequence[ChecksumEvmAddress],
) -> None:
    """Flag for redecoding the transactions with logs of the contracts of tokens that were
    just created, to decode the events that were skipped for lack of the tokens. There are no
    events of them yet. The logs have no index on their address, so all the tokens are searched
    for in a single scan instead of one per token."""
    if len(addresses) == 0:
        return

    _flag_transactions_for_redecoding(
        database=database,
        chain_id=chain_id,
        select_query=(
            'evmtx_receipt_logs AS L JOIN evm_transactions AS E ON E.identifier=L.tx_id '
            'WHERE E.chain_id=? AND L.address IN (%s)'
        ),
        values=addresses,
    )


def redecode_pending_token_txs(
        database: DBHandler,
        mark: TokenDetailsRetryMark,
) -> bool:
    """Redecode the transactions of a marked token whose details changed since it was marked,
    which happens if a previous run stopped after writing them and before redecoding, or if
    someone else changed them. It does not depend on what the nodes return, so a token whose
    queries stop answering is not given up with its events calculated with the old details.

    Returns whether there was anything pending, in which case the mark was updated.
    """
    if mark.saved is None:
        return False

    identifier = evm_address_to_identifier(address=mark.address, chain_id=mark.chain_id)
    with GlobalDBHandler().conn.read_ctx() as cursor:
        if (current := cursor.execute(TOKEN_DETAILS_QUERY, (identifier,)).fetchone()) is None:
            return False

    if len(changed := frozenset(
        prop for prop in mark.missing
        if current[TOKEN_DETAILS_INDEX[prop]] != mark.saved[TOKEN_DETAILS_INDEX[prop]]
    )) == 0:
        return False

    redecode_token_txs(database=database, chain_id=mark.chain_id, address=mark.address)
    finish_token_details_retry(
        chain_id=mark.chain_id,
        address=mark.address,
        saved=SavedDetails(
            written=frozenset(),
            redecode=True,
            remaining=mark.missing - changed,
            saved=current,
        ),
    )
    return True
