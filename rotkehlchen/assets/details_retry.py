"""Bookkeeping of erc20 tokens whose details have to be queried again.

A token whose details could not be fully queried when first seen is marked in the global DB
unique cache by chain and address. The mark keeps the details saved in the token and which of
them are only defaults or fallbacks, plus how many retries found them incomplete. When the
attempts run out, or the user edits the token, the mark moves to a given up key and the token is
never retried again. When the details of a token change, or a token that could not be created
gets created, the transactions affected are flagged for redecoding.
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
# runs that can postpone a token, since nothing answered, before one counts as an attempt
TOKEN_DETAILS_RETRY_MAX_POSTPONES: Final = 24
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
    # runs in a row that postponed it instead of counting an attempt
    postponed: int = 0
    # whether it is saved in the global DB. A token with its identifier as name that is not
    # marked is retried with a mark that is not saved, having the details it was selected with.
    persisted: bool = True


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
    """Whether the details of the token are never queried again"""
    with GlobalDBHandler().conn.read_ctx() as cursor:
        return _is_given_up(cursor=cursor, chain_id=chain_id, address=address)


def _serialize_mark(
        attempts: int,
        saved: TokenDetails | None,
        missing: frozenset[str] = frozenset(ERC20_PROPERTIES),
        given: Mapping[str, Any] | None = None,
        postponed: int = 0,
) -> str:
    return rlk_jsondumps({
        'postponed': postponed,
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
    """Mark a token to have its details queried again, keeping the attempts of an existing
    mark and skipping given up tokens. missing are the ERC20_PROPERTIES whose saved values are
    only defaults or fallbacks. given are the details supplied by the caller for a token that
    could not be created, merged with the ones of earlier sightings."""
    key_parts = _mark_key_parts(chain_id=chain_id, address=address)
    # runs for every sighting while decoding, so only write when needed
    with GlobalDBHandler().conn.read_ctx() as cursor:
        if _is_given_up(cursor=cursor, chain_id=chain_id, address=address):
            return

        existing = globaldb_get_unique_cache_value(cursor=cursor, key_parts=key_parts)

    attempts = 0
    if existing is not None and (old := _deserialize_mark(chain_id, address, existing)) is not None:  # noqa: E501
        attempts = old.attempts
        if saved is None and old.saved is None:  # still not created
            given = {**old.given, **({} if given is None else given)}
            missing = frozenset(ERC20_PROPERTIES) - given.keys()  # the rest is queried

        if old.saved == saved and old.missing == missing and old.given == ({} if given is None else given):  # noqa: E501
            return  # already marked as it is now. Keep its place in the queue

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
            missing=frozenset(data['missing']),
            given=data['given'],
            postponed=data.get('postponed', 0),
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


def _is_current(cursor: DBCursor, mark: TokenDetailsRetryMark) -> bool:
    """Whether the mark is still the one of the token, so that the result of querying it can be
    written. While it was queried the token may have been edited by the user, deleted, which
    removes its bookkeeping, or marked again by a decoder that saw it."""
    if _is_given_up(cursor=cursor, chain_id=mark.chain_id, address=mark.address):
        return False

    stored = globaldb_get_unique_cache_value(
        cursor=cursor,
        key_parts=_mark_key_parts(chain_id=mark.chain_id, address=mark.address),
    )
    if mark.persisted is False:  # its identifier as name and not marked, with the same details
        return stored is None and _read_token_details(
            write_cursor=cursor,
            identifier=evm_address_to_identifier(address=mark.address, chain_id=mark.chain_id),
        ) == mark.saved

    return stored is not None and _deserialize_mark(
        chain_id=mark.chain_id,
        address=mark.address,
        value=stored,
    ) == mark


def remove_token_details_retry_mark(
        chain_id: ChainID,
        address: ChecksumEvmAddress,
        only_created: bool = False,
) -> None:
    """Remove the retry mark of a token. With only_created the mark is only removed if it is of
    a token that was not created when marked and exists now, checked in the deletion transaction.
    Any other mark was written after the caller read it and still tracks what to recover."""
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
    """Never query again the details of a token, since the user edited them.

    Returns whether the token was marked, which means its events may have amounts calculated
    with details that were not the right ones.
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
    """Move marks to the back of the queue without counting an attempt, since nothing answered
    and it can be an outage. If that goes on for TOKEN_DETAILS_RETRY_MAX_POSTPONES runs it is
    the token that fails, for example if it is the only one left on its chain, so it counts.
    A mark that changed while it was queried is left as it is now."""
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        for mark in marks:
            if not _is_current(cursor=write_cursor, mark=mark):
                continue

            if (postponed := mark.postponed + 1) >= TOKEN_DETAILS_RETRY_MAX_POSTPONES:
                _count_attempt(write_cursor=write_cursor, mark=mark)
                continue

            globaldb_set_unique_cache_value(  # also moves it to the back of the queue
                write_cursor=write_cursor,
                key_parts=_mark_key_parts(chain_id=mark.chain_id, address=mark.address),
                value=_serialize_mark(
                    attempts=mark.attempts,
                    saved=mark.saved,
                    missing=mark.missing,
                    given=mark.given,
                    postponed=postponed,
                ),
            )


def _count_attempt(write_cursor: DBCursor, mark: TokenDetailsRetryMark) -> None:
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
    not marked. When the attempts run out the token is given up. A mark that changed while it
    was queried is left as it is now."""
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        if _is_current(cursor=write_cursor, mark=mark):
            _count_attempt(write_cursor=write_cursor, mark=mark)


def _read_token_details(write_cursor: DBCursor, identifier: str) -> TokenDetails | None:
    """Read the name, symbol and decimals of a token. None if it does not exist"""
    return write_cursor.execute(TOKEN_DETAILS_QUERY, (identifier,)).fetchone()


def save_found_token_details(
        chain_id: ChainID,
        address: ChecksumEvmAddress,
        mark: TokenDetailsRetryMark,
        expected: TokenDetails,
        found: Mapping[str, Any],
) -> SavedDetails | None:
    """Save the queried details of an existing token and update its mark, in a single global
    DB write transaction so a user edit or asset update can't land between check and write.
    Only the needed details (the missing ones of the mark) that still have the value they had
    in expected are written.

    If details were written, or someone else changed them since the token was marked, its
    events used the old ones: the mark is written with expected and the caller has to
    redecode and call finish_token_details_retry. Otherwise the mark is removed when nothing is
    missing anymore, or an attempt is counted.

    The caller has to hold the token lock, since a decoder with an older version of the token
    would write it back.

    Returns what was done, or None if the user edited the token or it was deleted.
    """
    needed = mark.missing
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
            redecode=len(written) != 0 or unchanged != needed,
            remaining=remaining,
            saved=tuple(written.get(prop, current[idx]) for prop, idx in TOKEN_DETAILS_INDEX.items()),  # type: ignore[arg-type]  # name, symbol, decimals  # noqa: E501
        )
        if saved.redecode:
            globaldb_set_unique_cache_value(  # keep the details its events were calculated with
                write_cursor=write_cursor,
                key_parts=_mark_key_parts(chain_id=chain_id, address=address),
                value=_serialize_mark(attempts=mark.attempts, saved=expected, missing=needed),
            )
        elif len(remaining) == 0:
            _delete_mark(write_cursor=write_cursor, chain_id=chain_id, address=address)
        else:
            _count_attempt(write_cursor=write_cursor, mark=TokenDetailsRetryMark(
                chain_id=chain_id,
                address=address,
                attempts=mark.attempts,
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
    """Update the mark of a token after its transactions were redecoded: remove it if nothing
    is missing anymore, or keep only the missing details. Does nothing if the mark was removed
    or the user edited the token meanwhile."""
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        if _is_given_up(cursor=write_cursor, chain_id=chain_id, address=address):
            return

        key_parts = _mark_key_parts(chain_id=chain_id, address=address)
        if (existing := globaldb_get_unique_cache_value(cursor=write_cursor, key_parts=key_parts)) is None:  # noqa: E501
            return

        if len(saved.remaining) == 0:
            _delete_mark(write_cursor=write_cursor, chain_id=chain_id, address=address)
            return

        old = _deserialize_mark(chain_id=chain_id, address=address, value=existing)
        globaldb_set_unique_cache_value(
            write_cursor=write_cursor,
            key_parts=key_parts,
            value=_serialize_mark(
                attempts=0 if old is None else old.attempts,
                saved=saved.saved,
                missing=saved.remaining,
                given=None if old is None else old.given,
            ),
        )


def get_given_up_tokens_added_since(chain_id: ChainID) -> list[ChecksumEvmAddress]:
    """Return the tokens that were given up before they could be created and exist now, whose
    transactions have to be redecoded. Afterwards clear_given_up_attempts has to be called, so
    that a crash in between does not lose the redecoding."""
    with GlobalDBHandler().conn.read_ctx() as cursor:  # not under the write lock, rarely finds any
        return [row[0] for row in cursor.execute(
            'SELECT B.address FROM evm_tokens AS B JOIN unique_cache AS U '
            'ON U.key=? || B.chain || B.address WHERE B.chain=? '
            "AND json_extract(U.value, '$.saved') IS NULL "
            "AND json_extract(U.value, '$.attempts') > 0",
            (CacheType.TOKEN_DETAILS_GIVEN_UP.serialize(), chain_id.serialize_for_db()),
        )]


def clear_given_up_attempts(chain_id: ChainID, addresses: Sequence[ChecksumEvmAddress]) -> None:
    """Clear the attempts kept by given up tokens that were added. Only existing entries are
    updated, since a deleted token's entries must not be recreated by a stale cleanup."""
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
    """Flag for redecoding the transactions with events of the token, whose amounts were
    calculated with details it does not have anymore."""
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
    """Flag for redecoding the transactions with logs of the contracts of just created tokens,
    to decode the events skipped for lack of them. The logs have no index on their address, so
    all the tokens are searched in a single scan."""
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
    which happens if a run stopped after writing them, or someone else changed them. It does
    not depend on the nodes, so a token that stops answering is not given up with stale events.

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
