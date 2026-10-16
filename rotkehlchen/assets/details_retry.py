"""Bookkeeping of erc20 tokens whose details have to be queried again.

A token whose details could not be fully queried when first seen is marked in the global DB
unique cache by chain and address. The mark keeps the details saved in the token and which of
them are only defaults or fallbacks, plus how many retries found them incomplete. When the
attempts run out, or the user edits the token, the mark moves to a given up key and the token is
never retried again.

The global DB is shared by all the users of the machine while their transactions are in their
own user DB. So when the details of a token change, or a token that could not be created gets
created, a redecode entry with an increasing sequence number is written for it in the same
global DB transaction. Each user DB keeps the sequence number of the last entry it applied, and
apply_token_details_redecodes flags the transactions of the newer entries for redecoding.
"""
import logging
from collections import defaultdict
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal, NamedTuple

from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.chain.evm.constants import ERC20_PROPERTIES
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.utils import get_query_chunks
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import (
    compute_cache_key,
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    EVM_CHAIN_IDS_WITH_TRANSACTIONS,
    CacheType,
    ChainID,
    ChecksumEvmAddress,
    EVMTxHash,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import ts_now_in_ms
from rotkehlchen.utils.serialization import jsonloads_dict, rlk_jsondumps

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from rotkehlchen.chain.aggregator import ChainsAggregator
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


def _like_prefix(cache_type: CacheType, chain_id: ChainID | None = None) -> str:
    """LIKE pattern of the unique cache keys of the type, for all chains or the given one"""
    prefix = compute_cache_key((cache_type,) if chain_id is None else (cache_type, str(chain_id.serialize_for_db())))  # noqa: E501
    # the 0x makes sure that a chain id is not the prefix of a longer one
    return prefix.replace('_', '\\_') + ('%' if chain_id is None else '0x%')


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


def _write_mark(write_cursor: DBCursor, mark: TokenDetailsRetryMark, given_up: bool = False) -> None:  # noqa: E501
    """Write the mark of a token, which also moves it to the back of the queue"""
    globaldb_set_unique_cache_value(
        write_cursor=write_cursor,
        key_parts=_mark_key_parts(chain_id=mark.chain_id, address=mark.address, given_up=given_up),
        value=_serialize_mark(
            attempts=mark.attempts,
            saved=mark.saved,
            missing=mark.missing,
            given=mark.given,
            postponed=mark.postponed,
        ),
    )


def _record_redecode(
        write_cursor: DBCursor,
        chain_id: ChainID,
        address: ChecksumEvmAddress,
        created: bool,
) -> None:
    """Make every user DB redecode the transactions of the token. Has to be called in the
    global DB transaction that changed what its events depend on, so that it can't be lost.

    created is for a token that could not be created before, whose transactions have no events
    of it and are found by the logs of its contract. A pending entry stays created, since a user
    that did not apply it yet still has to search the logs.
    """
    key_parts: tuple[Literal[CacheType.TOKEN_DETAILS_REDECODE], str, str] = (
        CacheType.TOKEN_DETAILS_REDECODE,
        str(chain_id.serialize_for_db()),
        address,
    )
    if not created and (existing := globaldb_get_unique_cache_value(cursor=write_cursor, key_parts=key_parts)) is not None:  # noqa: E501
        try:
            created = jsonloads_dict(existing)['created'] is True
        except (JSONDecodeError, KeyError):
            created = True  # scanning the logs too finds every transaction

    last_seq = write_cursor.execute(
        "SELECT MAX(CAST(json_extract(value, '$.seq') AS INTEGER)) FROM unique_cache "
        "WHERE key LIKE ? ESCAPE '\\'",
        (_like_prefix(CacheType.TOKEN_DETAILS_REDECODE),),
    ).fetchone()[0]
    globaldb_set_unique_cache_value(
        write_cursor=write_cursor,
        key_parts=key_parts,
        # never below the current time in ms, so a global DB that was replaced by an older
        # one can't reuse sequence numbers that the user DBs already applied
        value=rlk_jsondumps({'seq': max((last_seq or 0) + 1, ts_now_in_ms()), 'created': created}),
    )


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
    could not be created, merged with the ones of earlier sightings.

    If the token was marked when it could not be created and exists now, the transactions where
    its events were skipped have to be redecoded, which is recorded with the new mark.
    """
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

        if (
            saved is not None and
            (stored := globaldb_get_unique_cache_value(cursor=write_cursor, key_parts=key_parts)) is not None and  # noqa: E501
            (stored_mark := _deserialize_mark(chain_id, address, stored)) is not None and
            stored_mark.saved is None
        ):
            _record_redecode(write_cursor=write_cursor, chain_id=chain_id, address=address, created=True)  # noqa: E501

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


def _read_mark(
        cursor: DBCursor,
        chain_id: ChainID,
        address: ChecksumEvmAddress,
        given_up: bool = False,
) -> TokenDetailsRetryMark | None:
    if (value := globaldb_get_unique_cache_value(
        cursor=cursor,
        key_parts=_mark_key_parts(chain_id=chain_id, address=address, given_up=given_up),
    )) is None:
        return None

    return _deserialize_mark(chain_id=chain_id, address=address, value=value)


def get_token_details_retry_mark(
        chain_id: ChainID,
        address: ChecksumEvmAddress,
) -> TokenDetailsRetryMark | None:
    """Get the retry mark of a token, if it has one"""
    with GlobalDBHandler().conn.read_ctx() as cursor:
        return _read_mark(cursor=cursor, chain_id=chain_id, address=address)


def get_token_details_retry_marks(
        chain_id: ChainID,
        limit: int,
) -> list[TokenDetailsRetryMark]:
    """Get up to limit marked tokens of the chain, the least recently tried first"""
    prefix = compute_cache_key((CacheType.TOKEN_DETAILS_RETRY, str(chain_id.serialize_for_db())))
    marks = []
    with GlobalDBHandler().conn.read_ctx() as cursor:
        for key, value in cursor.execute(
            "SELECT key, value FROM unique_cache WHERE key LIKE ? ESCAPE '\\' "
            'ORDER BY last_queried_ts, key LIMIT ?',
            (_like_prefix(CacheType.TOKEN_DETAILS_RETRY, chain_id), limit),
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

    stored = _read_mark(cursor=cursor, chain_id=mark.chain_id, address=mark.address)
    if mark.persisted is False:  # its identifier as name and not marked, with the same details
        return stored is None and _read_token_details(
            cursor=cursor,
            identifier=evm_address_to_identifier(address=mark.address, chain_id=mark.chain_id),
        ) == mark.saved

    return stored == mark


def remove_token_details_retry_mark(chain_id: ChainID, address: ChecksumEvmAddress) -> None:
    """Remove the retry mark of a token"""
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        _delete_mark(write_cursor=write_cursor, chain_id=chain_id, address=address)


def stop_token_details_retry(
        chain_id: ChainID,
        address: ChecksumEvmAddress,
        added: bool = False,
) -> bool:
    """Never query again the details of a token, since the user added or edited it.

    If its events may have been calculated with other details, because it was marked or given
    up with details that were not the ones of the chain, or it was added and the transactions
    decoded before skipped its events, every user has to redecode its transactions. That is
    recorded in the same transaction that replaces the bookkeeping that tracked it.

    Returns whether a redecode was recorded, to apply it to the user DB.
    """
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        mark = _read_mark(cursor=write_cursor, chain_id=chain_id, address=address)
        given_up = _read_mark(cursor=write_cursor, chain_id=chain_id, address=address, given_up=True)  # noqa: E501
        created = added or (mark is not None and mark.saved is None) or (
            given_up is not None and given_up.saved is None and given_up.attempts != 0
        )
        if redecode := created or mark is not None or (given_up is not None and given_up.saved is not None):  # noqa: E501
            _record_redecode(write_cursor=write_cursor, chain_id=chain_id, address=address, created=created)  # noqa: E501

        _delete_mark(write_cursor=write_cursor, chain_id=chain_id, address=address)
        _write_mark(  # a given up entry with nothing pending
            write_cursor=write_cursor,
            mark=TokenDetailsRetryMark(chain_id=chain_id, address=address, attempts=0, saved=None),
            given_up=True,
        )

    return redecode


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
            else:
                _write_mark(write_cursor=write_cursor, mark=mark._replace(postponed=postponed))


def _count_attempt(write_cursor: DBCursor, mark: TokenDetailsRetryMark) -> None:
    attempts = mark.attempts + 1
    if given_up := attempts >= TOKEN_DETAILS_RETRY_MAX_ATTEMPTS:
        log.warning(
            'Giving up on querying the details of token %s at %s after %d attempts',
            mark.address, mark.chain_id.to_name(), attempts,
        )
        _delete_mark(write_cursor=write_cursor, chain_id=mark.chain_id, address=mark.address)

    _write_mark(
        write_cursor=write_cursor,
        mark=mark._replace(attempts=attempts, postponed=0),
        given_up=given_up,
    )


def count_token_details_retry_attempt(mark: TokenDetailsRetryMark) -> None:
    """Count a retry that found the details incomplete, creating the mark if the token was
    not marked. When the attempts run out the token is given up. A mark that changed while it
    was queried is left as it is now."""
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        if _is_current(cursor=write_cursor, mark=mark):
            _count_attempt(write_cursor=write_cursor, mark=mark)


def _read_token_details(cursor: DBCursor, identifier: str) -> TokenDetails | None:
    """Read the name, symbol and decimals of a token. None if it does not exist"""
    return cursor.execute(TOKEN_DETAILS_QUERY, (identifier,)).fetchone()


def save_found_token_details(
        mark: TokenDetailsRetryMark,
        expected: TokenDetails,
        found: Mapping[str, Any],
) -> frozenset[str] | None:
    """Save the queried details of an existing token and update its mark, in a single global
    DB write transaction so a user edit or asset update can't land between check and write.
    Only the needed details (the missing ones of the mark) that still have the value they had
    in expected, the saved details of the mark, are written.

    If details were written, or someone else changed them since the token was marked, its
    events used the old ones, so a redecode is recorded in the same transaction. The mark is
    removed when nothing is missing anymore. Otherwise it keeps the details still missing, and
    counts an attempt if nothing changed.

    The caller has to hold the token lock, since a decoder with an older version of the token
    would write it back.

    Returns the details written, or None if the user edited the token or it was deleted.
    """
    chain_id, address, needed = mark.chain_id, mark.address, mark.missing
    identifier = evm_address_to_identifier(address=address, chain_id=chain_id)
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        if _is_given_up(cursor=write_cursor, chain_id=chain_id, address=address):
            return None  # edited by the user, who has the last word

        if (current := _read_token_details(cursor=write_cursor, identifier=identifier)) is None:
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
        new_mark = TokenDetailsRetryMark(
            chain_id=chain_id,
            address=address,
            attempts=mark.attempts,
            saved=tuple(written.get(prop, current[idx]) for prop, idx in TOKEN_DETAILS_INDEX.items()),  # type: ignore[arg-type]  # name, symbol, decimals  # noqa: E501
            missing=remaining,
        )
        if changed := len(written) != 0 or unchanged != needed:
            _record_redecode(write_cursor=write_cursor, chain_id=chain_id, address=address, created=False)  # noqa: E501

        if len(remaining) == 0:
            _delete_mark(write_cursor=write_cursor, chain_id=chain_id, address=address)
        elif changed:  # progress was made, so no attempt is counted
            _write_mark(write_cursor=write_cursor, mark=new_mark)
        else:
            _count_attempt(write_cursor=write_cursor, mark=new_mark)

    AssetResolver.clean_memory_cache(identifier)  # so the token is loaded from the DB
    return frozenset(written)


def _changed_mark_details(
        cursor: DBCursor,
        mark: TokenDetailsRetryMark,
) -> tuple[TokenDetailsRetryMark | None, TokenDetails | None, frozenset[str]]:
    """Read the stored mark of a token, the details the token has now and which of the missing
    details of the mark changed since it was marked"""
    if (stored := _read_mark(cursor=cursor, chain_id=mark.chain_id, address=mark.address)) is None:
        return None, None, frozenset()

    if stored.saved is None or (current := _read_token_details(
        cursor=cursor,
        identifier=evm_address_to_identifier(address=mark.address, chain_id=mark.chain_id),
    )) is None:
        return stored, None, frozenset()

    return stored, current, frozenset(
        prop for prop in stored.missing
        if current[TOKEN_DETAILS_INDEX[prop]] != stored.saved[TOKEN_DETAILS_INDEX[prop]]
    )


def settle_changed_token_marks(marks: list[TokenDetailsRetryMark]) -> list[TokenDetailsRetryMark]:
    """Settle the marks of tokens whose missing details changed since they were marked, for
    example by an asset update: the changed details are not missing anymore, and every user
    has to redecode the transactions of the token. It is done before querying them, so it does
    not depend on the nodes and a token that stops answering is not given up with events
    calculated with stale details. The write lock is only taken if a mark has to be settled.

    Returns the marks as they are now, without the ones that were removed or have nothing
    missing anymore.
    """
    result: list[TokenDetailsRetryMark] = []
    to_settle: list[TokenDetailsRetryMark] = []
    with GlobalDBHandler().conn.read_ctx() as cursor:
        for mark in marks:
            if mark.persisted is False:
                result.append(mark)
            elif (details := _changed_mark_details(cursor=cursor, mark=mark))[0] is not None:
                (to_settle if len(details[2]) != 0 else result).append(details[0])
            # else removed after it was loaded

    if len(to_settle) == 0:
        return result

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        for mark in to_settle:  # read again under the write lock
            stored, current, changed = _changed_mark_details(cursor=write_cursor, mark=mark)
            if stored is None:
                continue

            if current is None or len(changed) == 0:
                result.append(stored)
                continue

            _record_redecode(write_cursor=write_cursor, chain_id=mark.chain_id, address=mark.address, created=False)  # noqa: E501
            if len(remaining := stored.missing - changed) == 0:
                _delete_mark(write_cursor=write_cursor, chain_id=mark.chain_id, address=mark.address)  # noqa: E501
            else:
                _write_mark(write_cursor=write_cursor, mark=(stored := stored._replace(saved=current, missing=remaining)))  # noqa: E501
                result.append(stored)

    return result


def settle_created_token_marks(chain_id: ChainID, addresses: Sequence[ChecksumEvmAddress]) -> None:
    """Remove the marks of tokens that could not be created when marked and exist now, recording
    in the same transaction that every user has to redecode the transactions with logs of their
    contracts, where their events were skipped. Marks written since with details of the token,
    or of a token deleted meanwhile, are left alone."""
    if len(addresses) == 0:
        return

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        for address in addresses:
            write_cursor.execute(
                "DELETE FROM unique_cache WHERE key=? AND json_extract(value, '$.saved') IS NULL "
                'AND EXISTS (SELECT 1 FROM evm_tokens WHERE identifier=?)',
                (
                    compute_cache_key(_mark_key_parts(chain_id=chain_id, address=address)),
                    evm_address_to_identifier(address=address, chain_id=chain_id),
                ),
            )
            if write_cursor.rowcount != 0:
                _record_redecode(write_cursor=write_cursor, chain_id=chain_id, address=address, created=True)  # noqa: E501


def _given_up_change(
        cursor: DBCursor,
        chain_id: ChainID,
        address: ChecksumEvmAddress,
) -> tuple[TokenDetailsRetryMark, TokenDetails] | None:
    """Return the given up entry of a token and its details now, if the entry has to be
    settled: the token was given up before it could be created and exists now, or the missing
    details it was given up with changed."""
    if (
        (entry := _read_mark(cursor=cursor, chain_id=chain_id, address=address, given_up=True)) is None or  # noqa: E501
        (current := _read_token_details(
            cursor=cursor,
            identifier=evm_address_to_identifier(address=address, chain_id=chain_id),
        )) is None
    ):
        return None

    if entry.saved is None:
        return (entry, current) if entry.attempts != 0 else None

    if any(
        current[TOKEN_DETAILS_INDEX[prop]] != entry.saved[TOKEN_DETAILS_INDEX[prop]]
        for prop in entry.missing
    ):
        return entry, current

    return None


def settle_given_up_tokens(chain_id: ChainID) -> None:
    """Record that every user has to redecode the transactions of the given up tokens of the
    chain that changed without being queried: added after being given up before they could be
    created, or with missing details that changed, for example by an asset update. The given up
    entry is updated in the same transaction, so that each change is recorded once.
    The given up entries are few, so their tokens are looked up one by one, and the write lock
    is only taken if one has to be settled.
    """
    prefix = compute_cache_key((CacheType.TOKEN_DETAILS_GIVEN_UP, str(chain_id.serialize_for_db())))  # noqa: E501
    addresses: list[ChecksumEvmAddress] = []
    with GlobalDBHandler().conn.read_ctx() as cursor:
        for (key,) in cursor.execute(
            "SELECT key FROM unique_cache WHERE key LIKE ? ESCAPE '\\' AND "
            "(json_extract(value, '$.saved') IS NOT NULL OR json_extract(value, '$.attempts') > 0)",  # noqa: E501
            (_like_prefix(CacheType.TOKEN_DETAILS_GIVEN_UP, chain_id),),
        ).fetchall():  # the cursor is used for the lookups below
            address = ChecksumEvmAddress(key[len(prefix):])
            if _given_up_change(cursor=cursor, chain_id=chain_id, address=address) is not None:
                addresses.append(address)

    if len(addresses) == 0:
        return

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        for address in addresses:  # read again under the write lock
            if (change := _given_up_change(cursor=write_cursor, chain_id=chain_id, address=address)) is None:  # noqa: E501
                continue

            entry, current = change
            _record_redecode(write_cursor=write_cursor, chain_id=chain_id, address=address, created=entry.saved is None)  # noqa: E501
            _write_mark(  # nothing pending anymore
                write_cursor=write_cursor,
                mark=entry._replace(attempts=0) if entry.saved is None else entry._replace(saved=current),  # noqa: E501
                given_up=True,
            )


def _get_pending_redecodes(after_seq: int) -> list[tuple[ChainID, ChecksumEvmAddress, bool, int]]:
    """Get the (chain, address, created, sequence number) of the token redecode entries with a
    sequence number after the given one"""
    prefix = CacheType.TOKEN_DETAILS_REDECODE.serialize()
    result = []
    with GlobalDBHandler().conn.read_ctx() as cursor:
        for key, value in cursor.execute(
            "SELECT key, value FROM unique_cache WHERE key LIKE ? ESCAPE '\\' "
            "AND CAST(json_extract(value, '$.seq') AS INTEGER) > ?",
            (_like_prefix(CacheType.TOKEN_DETAILS_REDECODE), after_seq),
        ):
            chain, address = key[len(prefix):].split('0x', maxsplit=1)
            try:
                data = jsonloads_dict(value)
                result.append((
                    ChainID.deserialize_from_db(int(chain)),
                    ChecksumEvmAddress('0x' + address),
                    data['created'] is True,
                    int(data['seq']),
                ))
            except (JSONDecodeError, KeyError, ValueError, DeserializationError) as e:
                log.error('Skipping malformed token redecode entry %s due to %s', key, e)

    return result


def _find_transactions(
        cursor: DBCursor,
        chain_id: ChainID,
        select_query: str,
        values: Sequence[str],
) -> dict[int, EVMTxHash]:
    transactions: dict[int, EVMTxHash] = {}
    for chunk, placeholders in get_query_chunks(data=values):
        transactions |= {
            tx_id: deserialize_evm_tx_hash(tx_hash) for tx_id, tx_hash in cursor.execute(
                f'SELECT DISTINCT E.identifier, E.tx_hash FROM {select_query % placeholders}',
                (chain_id.serialize_for_db(), *chunk),
            )
        }

    return transactions


def _flag_token_transactions(
        database: DBHandler,
        chain_id: ChainID,
        tokens: Mapping[ChecksumEvmAddress, bool],
) -> None:
    """Flag for redecoding the transactions with events of the given tokens, whose amounts
    were calculated with details they don't have anymore. For the ones that were created, given
    as True, also the transactions with logs of their contracts, whose events were skipped.
    The logs have no index on their address, so all of them are searched in a single scan."""
    from rotkehlchen.db.evmtx import DBEvmTx  # avoid circular import
    with database.conn.read_ctx() as cursor:  # the logs query is slow. Not under the write lock
        transactions = _find_transactions(
            cursor=cursor,
            chain_id=chain_id,
            select_query=(
                'history_events AS H JOIN chain_events_info AS C ON H.identifier=C.identifier '
                'JOIN evm_transactions AS E ON E.tx_hash=C.tx_ref WHERE E.chain_id=? AND H.asset IN (%s)'  # noqa: E501
            ),
            values=[evm_address_to_identifier(address=x, chain_id=chain_id) for x in tokens],
        )
        if len(created := [address for address, is_created in tokens.items() if is_created]) != 0:
            transactions |= _find_transactions(
                cursor=cursor,
                chain_id=chain_id,
                select_query=(
                    'evmtx_receipt_logs AS L JOIN evm_transactions AS E ON E.identifier=L.tx_id '
                    'WHERE E.chain_id=? AND L.address IN (%s)'
                ),
                values=created,
            )

    with database.conn.write_ctx() as write_cursor:
        DBEvmTx(database).flag_transactions_for_redecoding(
            write_cursor=write_cursor,
            transactions=transactions,
            chain_id=chain_id,  # type: ignore[arg-type]  # only chains with transactions are given
        )


def apply_token_details_redecodes(chains_aggregator: ChainsAggregator) -> None:
    """Flag for redecoding in the user DB the transactions of the tokens with redecode entries
    it has not applied yet.

    A decoder decoding a transaction of one of the tokens may have loaded its old details
    without having saved the transaction as decoded yet. Flagging would skip it, and the
    decoder would then save events calculated with the old details. So the transactions of
    each chain are searched and flagged holding the lock of its decoder, which every decoding
    of transactions holds.

    The sequence number applied is saved only after flagging, so an interruption makes the next
    call do it again.
    """
    database = chains_aggregator.database
    with database.conn.read_ctx() as cursor:
        applied = int(database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.TOKEN_DETAILS_REDECODE_CURSOR,
        ) or 0)

    if len(pending := _get_pending_redecodes(after_seq=applied)) == 0:
        return

    by_chain: defaultdict[ChainID, dict[ChecksumEvmAddress, bool]] = defaultdict(dict)
    for chain_id, address, created, _ in pending:
        by_chain[chain_id][address] = created

    for chain_id, tokens in by_chain.items():
        if chain_id not in EVM_CHAIN_IDS_WITH_TRANSACTIONS:
            continue  # no transactions to redecode

        decoder = chains_aggregator.get_evm_manager(chain_id).transactions_decoder
        with decoder.undecoded_tx_query_lock:
            _flag_token_transactions(database=database, chain_id=chain_id, tokens=tokens)

    with database.conn.write_ctx() as write_cursor:
        current = int(database.get_static_cache(
            cursor=write_cursor,
            name=DBCacheStatic.TOKEN_DETAILS_REDECODE_CURSOR,
        ) or 0)
        database.set_static_cache(  # another call may have applied more meanwhile
            write_cursor=write_cursor,
            name=DBCacheStatic.TOKEN_DETAILS_REDECODE_CURSOR,
            value=str(max(current, *(seq for *_, seq in pending))),
        )
