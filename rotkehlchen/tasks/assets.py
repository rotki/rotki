import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Final, Literal

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import Asset, EvmToken, UnderlyingToken
from rotkehlchen.assets.details_retry import (
    TokenDetailsRetryMark,
    clear_given_up_attempts,
    count_token_details_retry_attempt,
    finish_token_details_retry,
    get_given_up_tokens_added_since,
    get_token_details_retry_mark,
    get_token_details_retry_marks,
    is_token_details_retry_given_up,
    postpone_token_details_retry,
    redecode_created_tokens_txs,
    redecode_pending_token_txs,
    redecode_token_txs,
    remove_token_details_retry_mark,
    save_found_token_details,
)
from rotkehlchen.assets.utils import (
    TokenEncounterInfo,
    check_if_spam_token,
    create_evm_token_if_missing,
    get_or_create_evm_token,
)
from rotkehlchen.chain.base.modules.aave.v3.constants import (
    AAVE_V3_DATA_PROVIDER as AAVE_V3_DATA_PROVIDER_BASE,
)
from rotkehlchen.chain.ethereum.modules.aave.v3.constants import (
    AAVE_V3_DATA_PROVIDER as AAVE_V3_DATA_PROVIDER_ETH,
    AAVE_V3_DATA_PROVIDER_OLD as AAVE_V3_DATA_PROVIDER_ETH_OLD,
    ETHERFI_AAVE_V3_DATA_PROVIDER as ETHERFI_AAVE_V3_DATA_PROVIDER_ETH,
    LIDO_AAVE_V3_DATA_PROVIDER as LIDO_AAVE_V3_DATA_PROVIDER_ETH,
)
from rotkehlchen.chain.ethereum.modules.spark.constants import (
    SPARK_DATA_PROVIDER as SPARK_DATA_PROVIDER_ETH,
)
from rotkehlchen.chain.ethereum.utils import MULTICALL_CHUNKS
from rotkehlchen.chain.evm.constants import ERC20_PROPERTIES, EVM_ADDRESS_REGEX, ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE_V3
from rotkehlchen.chain.evm.decoding.aave.v3.constants import (
    AAVE_V3_DATA_PROVIDER as AAVE_V3_DATA_PROVIDER_EVM,
)
from rotkehlchen.chain.evm.decoding.spark.constants import CPT_SPARK
from rotkehlchen.chain.evm.tokens import query_owned_erc721_tokens
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.gnosis.modules.aave.v3.constants import (
    AAVE_V3_DATA_PROVIDER as AAVE_V3_DATA_PROVIDER_GNO,
)
from rotkehlchen.chain.gnosis.modules.monerium.constants import (
    GNOSIS_MONERIUM_LEGACY_ADDRESSES,
    V1_TO_V2_MONERIUM_MAPPINGS as GNOSIS_MONERIUM_MAPPINGS,
)
from rotkehlchen.chain.gnosis.modules.spark.constants import (
    SPARK_DATA_PROVIDER as SPARK_DATA_PROVIDER_GNOSIS,
)
from rotkehlchen.chain.polygon_pos.modules.monerium.constants import (
    POLYGON_MONERIUM_LEGACY_ADDRESSES,
    V1_TO_V2_MONERIUM_MAPPINGS as POLYGON_MONERIUM_MAPPINGS,
)
from rotkehlchen.chain.scroll.modules.aave.v3.constants import (
    AAVE_V3_DATA_PROVIDER as AAVE_V3_DATA_PROVIDER_SCRL,
)
from rotkehlchen.constants.misc import ONE
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.constants import (
    CHAIN_EVENT_FIELDS,
    HISTORY_BASE_ENTRY_FIELDS,
)
from rotkehlchen.db.filtering import EVENTS_WITH_COUNTERPARTY_JOIN
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import NotERC20Conformant, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import (
    globaldb_general_cache_exists,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import (
    EventDirection,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import (
    CHAINID_TO_SUPPORTED_BLOCKCHAIN,
    EVM_CHAIN_IDS_WITH_TRANSACTIONS,
    EVM_LOCATIONS,
    SPAM_PROTOCOL,
    SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE,
    CacheType,
    ChainID,
    SupportedBlockchain,
    TokenKind,
)
from rotkehlchen.utils.misc import get_chunks, ts_now, ts_sec_to_ms

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.types import ChecksumEvmAddress, EVMTxHash


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

SYMBOL_AND_NAME_ASSETS_QUERY = (
    'SELECT C.symbol, A.name, A.identifier, B.chain FROM evm_tokens as B LEFT JOIN '
    'common_asset_details AS C ON C.identifier = B.identifier JOIN assets as A on '
    'A.identifier=B.identifier WHERE B.PROTOCOL IS NOT ? ORDER BY C.symbol'
)
TOKEN_DETAILS_RETRY_BATCH_SIZE: Final = 50
TOKEN_DETAILS_RETRY_CHUNK_SIZE: Final = 25
# single token queries that can fail in a row before the nodes are considered down
TOKEN_DETAILS_RETRY_MAX_FAILED_QUERIES: Final = 3
MULTISEND_SPAM_THRESHOLD = 50
KNOWN_FALSE_POSITIVES: Final = (
    {
    'eip155:1/erc20:0xA0b73E1Ff0B80914AB6fe0444E65848C4C34450b',  # crypto.com CRO token
    'eip155:1/erc20:0xB63B606Ac810a52cCa15e44bB630fd42D8d1d83d',  # crypto.com
    } |
    set(GNOSIS_MONERIUM_MAPPINGS.keys()) |
    set(GNOSIS_MONERIUM_MAPPINGS.values()) |
    set(POLYGON_MONERIUM_MAPPINGS.keys()) |
    set(POLYGON_MONERIUM_MAPPINGS.values())
)


def _add_spam_asset(
        detected_spam_assets: list[str],
        globaldb: GlobalDBHandler,
        user_db: DBHandler,
        user_db_cursor: DBCursor,
) -> None:
    """Updates the protocol to SPAM_PROTOCOL for the list of assets
    provided and also ignores it
    """
    with globaldb.conn.write_ctx() as write_cursor:
        query = 'UPDATE evm_tokens SET protocol=? WHERE identifier=?'
        write_cursor.executemany(
            query,
            [(SPAM_PROTOCOL, identifier) for identifier in detected_spam_assets],
        )

    user_db.ignore_multiple_assets(
        write_cursor=user_db_cursor,
        assets=detected_spam_assets,
    )


def autodetect_spam_assets_in_db(user_db: DBHandler) -> None:
    """
    Autodetect spam tokens already in the globaldb and ignore them.
    If any token gets detected a ws message will be sent to refresh balances for the chain
    where it was detected.
    """
    globaldb = GlobalDBHandler()
    detected_spam_assets = []
    chains_to_refresh: set[ChainID] = set()

    # Check if any tokens in the global DB not marked as spam are actually matching
    # the spam patterns
    with globaldb.conn.read_ctx() as cursor:
        cursor.execute(SYMBOL_AND_NAME_ASSETS_QUERY, (SPAM_PROTOCOL,))
        for symbol, name, identifier, chain_id in cursor:
            if identifier in KNOWN_FALSE_POSITIVES:
                continue

            if check_if_spam_token(symbol=symbol, name=name) is False:
                continue

            # check if the asset is whitelisted and skip if it is
            with GlobalDBHandler().conn.read_ctx() as globaldb_cursor:
                if globaldb_general_cache_exists(
                    cursor=globaldb_cursor,
                    key_parts=(CacheType.SPAM_ASSET_FALSE_POSITIVE,),
                    value=identifier,
                ):
                    continue

            deserialized_chain_id = ChainID.deserialize_from_db(chain_id)
            detected_spam_assets.append(identifier)
            chains_to_refresh.add(deserialized_chain_id)
            log.debug(f'Detected spam token {identifier} at chain {deserialized_chain_id}')

    if len(detected_spam_assets) == 0:
        with user_db.conn.write_ctx() as write_cursor:
            write_cursor.execute(  # remember last time spam detection ran
                'INSERT OR REPLACE INTO key_value_cache (name, value) VALUES (?, ?)',
                (DBCacheStatic.LAST_SPAM_ASSETS_DETECT_KEY.value, str(ts_now())),
            )
        return

    # update the user list of ignored assets
    with user_db.conn.write_ctx() as write_cursor:
        _add_spam_asset(
            detected_spam_assets=detected_spam_assets,
            globaldb=globaldb,
            user_db=user_db,
            user_db_cursor=write_cursor,
        )
        write_cursor.execute(  # remember last time spam detection ran
            'INSERT OR REPLACE INTO key_value_cache (name, value) VALUES (?, ?)',
            (DBCacheStatic.LAST_SPAM_ASSETS_DETECT_KEY.value, str(ts_now())),
        )

    for chain in chains_to_refresh:
        if chain not in CHAINID_TO_SUPPORTED_BLOCKCHAIN:
            continue

        user_db.msg_aggregator.add_message(
            message_type=WSMessageType.REFRESH_BALANCES,
            data={
                'type': 'blockchain_balances',
                'blockchain': chain.to_blockchain().serialize(),
            },
        )


def update_owned_assets(user_db: DBHandler) -> None:
    """Wrapper to be used in async task to update owned assets"""
    with user_db.conn.read_ctx() as cursor:
        user_db.update_owned_assets_in_globaldb(cursor=cursor)

    with user_db.conn.write_ctx() as write_cursor:
        write_cursor.execute(  # remember last task ran
            'INSERT OR REPLACE INTO key_value_cache (name, value) VALUES (?, ?)',
            (DBCacheStatic.LAST_OWNED_ASSETS_UPDATE.value, str(ts_now())),
        )


def _find_missing_tokens(
        token_to_underlying: dict[ChecksumEvmAddress, ChecksumEvmAddress],
        chain_id: ChainID,
) -> tuple[ChecksumEvmAddress, ...]:
    """Check if aave tokens are stored in the globaldb.
    We consider a token as stored when it has the aave v3 protocol set. This means that
    it was not added by decoders but by the logic of update_aave_v3_underlying_assets.

    Returns all tokens that are not stored in the global db with the correct protocol set.
    """
    with GlobalDBHandler().conn.read_ctx() as cursor:
        cursor.execute(
            'SELECT address, protocol FROM evm_tokens '
            f"WHERE address IN ({','.join('?' * len(token_to_underlying))}) "
            'AND chain=?',
            tuple(token_to_underlying.keys()) + (chain_id.serialize_for_db(),),
        )

        missing_tokens = set(token_to_underlying.keys())
        for row in cursor:
            if row[1] == CPT_AAVE_V3:
                missing_tokens.remove(row[0])

    return tuple(missing_tokens)


def _batch_query_properties(
        node_inquirer: EvmNodeInquirer,
        addresses: tuple[ChecksumEvmAddress, ...],
) -> dict[ChecksumEvmAddress, tuple[str, str, int]]:
    """Query details for the provided addresses.
    It queries each property for all the tokens in a multicall.

    May raise:
    - RemoteError
    """
    contract = EvmContract(
        address=ZERO_ADDRESS,  # not important for the usage here
        abi=node_inquirer.contracts.erc20_abi,
        deployed_block=0,
    )
    enc_name = contract.encode(method_name='name')
    enc_symbol = contract.encode(method_name='symbol')
    enc_decimals = contract.encode(method_name='decimals')
    values = []

    for method_name, encoded in zip(
        ('name', 'symbol', 'decimals'),
        (enc_name, enc_symbol, enc_decimals),
        strict=False,
    ):
        calls = [(address, encoded) for address in addresses]
        values.append([
            contract.decode(x, method_name)[0]
            for x in node_inquirer.multicall(calls)
        ])

    return {
        address: (values[0][idx], values[1][idx], values[2][idx])
        for idx, address in enumerate(addresses)
    }


def _get_tokens_missing_details(
        chain_ids: Sequence[ChainID],
        after_identifier: str,
) -> list[tuple[str, TokenDetailsRetryMark]]:
    """Get up to TOKEN_DETAILS_RETRY_BATCH_SIZE erc20 tokens of the given chains whose name is
    their identifier, which is what is saved when the details could not be queried, or NULL,
    which older versions saved when repairing them failed. Both show the identifier as name.
    Tokens are returned ordered by identifier, starting after the given one, with a mark that
    is not saved and has the details they have now, to detect a change while they are queried.
    """
    if len(chain_ids) == 0:
        return []

    with GlobalDBHandler().conn.read_ctx() as cursor:
        return [
            (identifier, TokenDetailsRetryMark(
                chain_id=ChainID.deserialize_from_db(chain),
                address=address,
                attempts=0,
                saved=(name, symbol, decimals),
            )) for identifier, chain, address, name, symbol, decimals in cursor.execute(
                'SELECT A.identifier, B.chain, B.address, A.name, C.symbol, B.decimals FROM '
                'assets AS A JOIN evm_tokens AS B ON A.identifier=B.identifier LEFT JOIN '
                'common_asset_details AS C ON C.identifier=A.identifier '
                'WHERE (A.name IS NULL OR A.name=A.identifier) '
                'AND B.token_kind=? '
                'AND B.protocol IS NOT ? AND A.identifier>? '
                # tokens edited by the user or given up are left as they are
                'AND NOT EXISTS (SELECT 1 FROM unique_cache WHERE key=? || B.chain || B.address) '
                f"AND B.chain IN ({','.join('?' * len(chain_ids))}) ORDER BY A.identifier LIMIT ?",
                (
                    TokenKind.ERC20.serialize_for_db(),
                    SPAM_PROTOCOL,
                    after_identifier,
                    CacheType.TOKEN_DETAILS_GIVEN_UP.serialize(),
                    *(chain_id.serialize_for_db() for chain_id in chain_ids),
                    TOKEN_DETAILS_RETRY_BATCH_SIZE,
                ),
            )
        ]


def _drop_resolved_token_marks(
        marks: list[TokenDetailsRetryMark],
) -> tuple[list[TokenDetailsRetryMark], list[ChecksumEvmAddress]]:
    """Remove the marks of tokens found to be spam after they were marked. The marks of tokens
    that could not be created when marked but exist now, for example after an asset update, are
    kept since their transactions have to be redecoded by the caller.

    Returns the marks that still have to be queried and the addresses of the tokens that exist
    now.
    """
    if len(marks) == 0:
        return marks, []

    chain_id = marks[0].chain_id
    with GlobalDBHandler().conn.read_ctx() as cursor:
        protocols = dict(cursor.execute(
            'SELECT address, protocol FROM evm_tokens WHERE chain=? AND address IN '
            f"({','.join('?' * len(marks))})",
            (chain_id.serialize_for_db(), *(x.address for x in marks)),
        ))

    remaining, added = [], []
    for mark in marks:
        if protocols.get(mark.address) != SPAM_PROTOCOL:
            if mark.saved is not None or mark.address not in protocols:
                remaining.append(mark)  # still has to be queried
            else:  # could not be created when marked, but exists now
                added.append(mark.address)
            continue

        remove_token_details_retry_mark(chain_id=chain_id, address=mark.address)

    return remaining, added


def _create_deferred_token(
        database: DBHandler,
        chain_id: ChainID,
        address: ChecksumEvmAddress,
        info: dict[str, Any],
) -> bool:
    """Create a token that could not be created when marked, with the details given by the
    caller plus the queried ones, the given ones winning. The mark is read again under the
    token lock since a decoder may have supplied more details meanwhile. If they are still
    incomplete an attempt is counted.

    Returns whether the token exists now, so the caller redecodes its transactions.
    """
    with database.get_or_create_token_lock:
        if (
            (latest := get_token_details_retry_mark(chain_id=chain_id, address=address)) is None or
            is_token_details_retry_given_up(chain_id=chain_id, address=address)
        ):
            return False  # removed, or edited by the user, meanwhile

        if latest.saved is not None:  # created meanwhile, and now tracked as any other token
            return True  # its transactions still have to be redecoded. The mark is kept

        if any(prop not in (details := {**info, **latest.given}) for prop in ERC20_PROPERTIES):
            count_token_details_retry_attempt(mark=latest)
            return False

        if create_evm_token_if_missing(
            userdb=database,
            chain_id=chain_id,
            address=address,
            name=details['name'],
            symbol=details['symbol'],
            decimals=details['decimals'],
        ):
            log.debug(
                'Created token %s at %s with its queried details',
                address, chain_id.to_name(),
            )

    return True  # also if it was added meanwhile


def _save_found_token_details(
        database: DBHandler,
        mark: TokenDetailsRetryMark,
        info: dict[str, Any],
) -> bool:
    """Save the queried details of a token that was missing them. info has only the details
    that the query returned.

    Only the details missing in the mark are saved, and only if they still have the value they
    had when it was selected or marked, since a user edit, an asset update or a decoder may have
    changed the token while its details were queried. See save_found_token_details.

    A token that could not be created when marked is created once the details given by the
    caller plus the queried ones are complete, with the given ones winning. Otherwise an
    attempt is counted.

    Returns whether such a token exists now, so the caller redecodes the transactions where it
    was seen, which were skipped for lack of the token, and then removes its mark.
    """
    chain_id, address = mark.chain_id, mark.address
    if mark.saved is None:  # the token could not be created at the time
        return _create_deferred_token(database=database, chain_id=chain_id, address=address, info=info)  # noqa: E501

    with database.get_or_create_token_lock:  # a decoder with an older version of the token would overwrite it  # noqa: E501
        saved = save_found_token_details(
            chain_id=chain_id,
            address=address,
            mark=mark,
            expected=mark.saved,
            found=info,
        )

    identifier = evm_address_to_identifier(address=address, chain_id=chain_id)
    if saved is None:
        log.debug('Token %s was edited by the user or deleted while its details were queried', identifier)  # noqa: E501
    elif saved.redecode:
        # the amounts of its events were calculated with the details it had when marked
        log.debug('Updated the details %s of token %s', sorted(saved.written), identifier)
        redecode_token_txs(database=database, chain_id=chain_id, address=address)
        finish_token_details_retry(chain_id=chain_id, address=address, saved=saved)

    return False


def _count_attempts(marks: list[TokenDetailsRetryMark]) -> None:
    """Count a failed attempt for each of the marks and clear the list"""
    for mark in marks:
        count_token_details_retry_attempt(mark=mark)

    marks.clear()


def _nodes_answer_again(node_inquirer: EvmNodeInquirer, answered: list[ChecksumEvmAddress]) -> bool:  # noqa: E501
    """Query again the token that answered most recently in the run to tell if the nodes are
    up. False if they fail or no token answered yet."""
    if len(answered) == 0:
        return False

    try:
        node_inquirer.get_multiple_erc20_contracts_info([answered[-1]])
    except RemoteError:
        return False

    return True


def _query_tokens_one_by_one(
        chain_id: ChainID,
        node_inquirer: EvmNodeInquirer,
        chunk: list[TokenDetailsRetryMark],
        failed: list[TokenDetailsRetryMark],
        answered_in_run: list[ChecksumEvmAddress],
) -> tuple[dict[ChecksumEvmAddress, dict[str, Any]], set[ChecksumEvmAddress], bool]:
    """Query the tokens of a chunk that failed one at a time, so a token that makes the query
    fail does not take the rest of the chunk with it.

    failed has the tokens that failed in a row so far in the run, maybe from previous chunks.
    A query that succeeds after them means they failed on their own, so they count an attempt.
    When TOKEN_DETAILS_RETRY_MAX_FAILED_QUERIES fail in a row a token that already answered in
    the run is queried again: if it answers the streak failed on its own and the run goes on,
    otherwise the nodes are considered down and querying stops.

    Returns the details found, the addresses whose query succeeded and whether the nodes are
    considered down.
    """
    infos: dict[ChecksumEvmAddress, dict[str, Any]] = {}
    answered: set[ChecksumEvmAddress] = set()
    for mark in chunk:
        try:
            infos |= node_inquirer.get_multiple_erc20_contracts_info([mark.address])
        except RemoteError as e:
            log.warning(
                'Failed to query the details of token %s at %s due to %s',
                mark.address, chain_id.to_name(), e,
            )
            failed.append(mark)
            if len(failed) == TOKEN_DETAILS_RETRY_MAX_FAILED_QUERIES:
                if not _nodes_answer_again(node_inquirer=node_inquirer, answered=answered_in_run):
                    return infos, answered, True

                _count_attempts(failed)
        else:
            answered.add(mark.address)
            answered_in_run.append(mark.address)
            _count_attempts(failed)

    return infos, answered, False


def _redecode_pending_tokens(
        database: DBHandler,
        marks: list[TokenDetailsRetryMark],
) -> list[TokenDetailsRetryMark]:
    """Finish the redecoding that an interrupted run left pending for the marked tokens whose
    details changed since they were marked, before querying them, so it is done even if the
    nodes keep returning nothing for them and they run out of attempts.

    Returns the marks as they are now, without the ones that are done.
    """
    result: list[TokenDetailsRetryMark] = []
    for mark in marks:
        if redecode_pending_token_txs(database=database, mark=mark):
            new_mark = get_token_details_retry_mark(chain_id=mark.chain_id, address=mark.address)
            if new_mark is not None:  # otherwise nothing is missing anymore
                result.append(new_mark)
        else:
            result.append(mark)

    return result


def _retry_chain_token_details(
        database: DBHandler,
        chain_id: ChainID,
        node_inquirer: EvmNodeInquirer,
        marks: list[TokenDetailsRetryMark],
) -> list[ChecksumEvmAddress]:
    """Query in chunks the details of the given tokens of a chain and save the ones that came
    back, as long as they are among the ones the token is missing. A token with some missing
    details still not returned counts a failed attempt and keeps only those as missing.

    Returns the tokens that could not be created when marked and exist now. The caller
    redecodes the transactions where they were seen and removes their marks.

    A single token can make the query of its whole chunk fail, for example a contract that
    burns all the gas, so a failed chunk is queried again one token at a time. A token that
    fails on its own counts a failed attempt. When TOKEN_DETAILS_RETRY_MAX_FAILED_QUERIES
    single queries fail in a row, at any point of the run, the nodes are probably down: the run
    stops and the tokens that failed go to the back of the queue without counting an attempt.
    """
    failed: list[TokenDetailsRetryMark] = []
    answered_in_run: list[ChecksumEvmAddress] = []
    created: list[ChecksumEvmAddress] = []
    nodes_down = False
    for chunk in get_chunks(_redecode_pending_tokens(database=database, marks=marks), TOKEN_DETAILS_RETRY_CHUNK_SIZE):  # noqa: E501
        try:
            infos = node_inquirer.get_multiple_erc20_contracts_info([x.address for x in chunk])
        except RemoteError as e:
            log.warning(
                'Failed to query token details at %s due to %s. Querying them one by one',
                chain_id.to_name(), e,
            )
            infos, answered, nodes_down = _query_tokens_one_by_one(
                chain_id=chain_id,
                node_inquirer=node_inquirer,
                chunk=chunk,
                failed=failed,
                answered_in_run=answered_in_run,
            )
        else:
            answered, nodes_down = {x.address for x in chunk}, False
            answered_in_run.extend(x.address for x in chunk)
            _count_attempts(failed)

        for mark in chunk:
            if (info := infos.get(mark.address)) is not None:
                if _save_found_token_details(database=database, mark=mark, info=info):
                    created.append(mark.address)
            elif mark.address in answered:  # the details came back incomplete
                _count_attempts([mark])

        if nodes_down:
            log.error('Stopping token details retry at %s since the nodes fail', chain_id.to_name())  # noqa: E501
            break

    if len(answered_in_run) != 0 and not nodes_down:  # the last queries failed while the nodes answered the rest  # noqa: E501
        _count_attempts(failed)
    else:
        postpone_token_details_retry(marks=failed)

    return created


def _redecode_created_tokens(
        database: DBHandler,
        chain_id: ChainID,
        given_up_added: list[ChecksumEvmAddress],
        marked_added: list[ChecksumEvmAddress],
        created: list[ChecksumEvmAddress],
) -> None:
    """Redecode the transactions of the tokens created in this run of a chain with a single scan
    of the logs. Only then are their marks removed and the attempts of the given up ones
    cleared, so an interruption makes the next run do it again.
    """
    if len(addresses := list(dict.fromkeys([*given_up_added, *marked_added, *created]))) == 0:
        return

    redecode_created_tokens_txs(database=database, chain_id=chain_id, addresses=addresses)
    clear_given_up_attempts(chain_id=chain_id, addresses=given_up_added)
    for address in [*marked_added, *created]:  # a mark of an existing token is still needed
        remove_token_details_retry_mark(chain_id=chain_id, address=address, only_created=True)


def retry_missing_token_details(chains_aggregator: ChainsAggregator) -> None:
    """Query again the details of tokens that are missing them: the ones saved with their
    identifier as name and the marked ones, whose query failed or returned only some details.
    Marked tokens that could not be created are created once their details are found.
    Transactions of tokens whose details change or that get created are flagged for redecoding.

    Every run goes through the next TOKEN_DETAILS_RETRY_BATCH_SIZE tokens with their identifier
    as name and the TOKEN_DETAILS_RETRY_BATCH_SIZE least recently tried marked tokens of each
    chain, in chunks per chain. The identifier of the last token without a mark is saved before
    querying so that tokens that keep failing can't block the rest. Tokens are given up after
    TOKEN_DETAILS_RETRY_MAX_ATTEMPTS runs that found their details incomplete.
    """
    with chains_aggregator.database.conn.read_ctx() as cursor:
        cursor_identifier = chains_aggregator.database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.TOKEN_DETAILS_RETRY_CURSOR,
        ) or ''

    # only chains where the user has accounts can be expected to have working nodes
    chain_ids = [
        chain_id for chain_id in EVM_CHAIN_IDS_WITH_TRANSACTIONS
        if len(chains_aggregator.accounts.get(chain_id.to_blockchain())) != 0
    ]
    tokens = _get_tokens_missing_details(chain_ids=chain_ids, after_identifier=cursor_identifier)
    with chains_aggregator.database.conn.write_ctx() as write_cursor:
        chains_aggregator.database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.TOKEN_DETAILS_RETRY_CURSOR,
            value=tokens[-1][0] if len(tokens) == TOKEN_DETAILS_RETRY_BATCH_SIZE else '',
        )
        chains_aggregator.database.set_static_cache(  # remember last task ran
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_TOKEN_DETAILS_RETRY_TS,
            value=ts_now(),
        )

    marks_by_chain: defaultdict[ChainID, dict[ChecksumEvmAddress, TokenDetailsRetryMark]] = defaultdict(dict)  # noqa: E501
    for _, mark in tokens:
        marks_by_chain[mark.chain_id][mark.address] = mark

    for chain_id in chain_ids:
        given_up_added = get_given_up_tokens_added_since(chain_id=chain_id)
        remaining, marked_added = _drop_resolved_token_marks(
            marks=get_token_details_retry_marks(chain_id=chain_id, limit=TOKEN_DETAILS_RETRY_BATCH_SIZE),  # noqa: E501
        )
        marks_by_chain[chain_id] |= {mark.address: mark for mark in remaining}
        created = _retry_chain_token_details(
            database=chains_aggregator.database,
            chain_id=chain_id,
            node_inquirer=chains_aggregator.get_evm_manager(chain_id=chain_id).node_inquirer,
            marks=list(marks_by_chain[chain_id].values()),
        ) if len(marks_by_chain[chain_id]) != 0 else []
        _redecode_created_tokens(
            database=chains_aggregator.database,
            chain_id=chain_id,
            given_up_added=given_up_added,
            marked_added=marked_added,
            created=created,
        )


def _update_lending_protocol_underlying_assets(
        chains_aggregator: ChainsAggregator,
        providers_info: Sequence[tuple[ChainID, ChecksumEvmAddress]],
        cache_key: DBCacheStatic,
        protocol: Literal['aave-v3', 'spark'],
) -> None:
    """Common logic to fetch the Aave v3 like underlying assets and populate `underlying_tokens_list` in globaldb

    This function is heavy since it makes several queries to external nodes. The logic has
    been refactored to do the following:

    1. Query all the reserver tokens (getAllReservesTokens).
    2. For each reserve token query the debt tokens (getReserveTokensAddresses).
    3. Check if we have the addresses for the debt tokens in the db.
    4. For the addresses we don't have in the db, query
    their properties (name, symbol, decimals).
    5. For each reserve token create it or ensure that the protocol is aave-v3 and the
    underlying token is set properly.
    """  # noqa: E501
    for chain_id, data_provider_address in providers_info:
        if len(chains_aggregator.accounts.get(chain_id.to_blockchain())) == 0:
            continue  # avoid querying chains without nodes connected

        node_inquirer = chains_aggregator.get_evm_manager(chain_id=chain_id).node_inquirer  # type: ignore[arg-type]  # all iterated ChainIDs are supported
        data_provider = node_inquirer.contracts.contract(address=data_provider_address)
        underlying_tokens = []

        try:
            for _, token_address in data_provider.call(
                node_inquirer=node_inquirer,
                method_name='getAllReservesTokens',
            ):  # get all the underlying tokens
                try:
                    underlying_tokens.append(deserialize_evm_address(token_address))
                except DeserializationError as e:
                    log.error(f'Failed to deserialize {protocol} underlying token address: {token_address} due to {e!s}')  # noqa: E501
                    continue

            reserve_tokens_raw = node_inquirer.multicall(
                calls=[(  # get all the reserve tokens for each underlying token
                    data_provider.address,
                    data_provider.encode(
                        method_name='getReserveTokensAddresses',
                        arguments=[underlying_token],
                    ),
                ) for underlying_token in underlying_tokens],
                calls_chunk_size=4 if chain_id in {ChainID.ARBITRUM_ONE, ChainID.BASE} else MULTICALL_CHUNKS,  # arbiscan and basescan API breaks with chunk_size > 4  # noqa: E501
            )
        except RemoteError as e:
            log.error(f'Failed to query {protocol} reserve tokens addresses due to {e!s}')
            continue

        # map debt tokens to underlying tokens. Underlying tokens have more than 1 debt token
        reserve_to_underlying = {}
        for underlying_token_address, tokens_raw in zip(underlying_tokens, reserve_tokens_raw, strict=False):  # noqa: E501
            for reserve in data_provider.decode(
                method_name='getReserveTokensAddresses',
                arguments=[underlying_token_address],
                result=tokens_raw,
            ):
                if (deserialized_reserve := deserialize_evm_address(reserve)) != ZERO_ADDRESS:
                    if deserialized_reserve in reserve_to_underlying:
                        continue  # the same token can appear multiple times
                    reserve_to_underlying[deserialized_reserve] = underlying_token_address

        # check the missing tokens and query their properties
        missing_tokens = _find_missing_tokens(reserve_to_underlying, node_inquirer.chain_id)
        try:
            address_to_properties = _batch_query_properties(node_inquirer, missing_tokens)
        except RemoteError as e:
            log.error(f'Failed to query {protocol} reserve tokens addresses due to {e!s}')
            continue

        # add the mappings of underlying tokens to the globaldb
        encounter = TokenEncounterInfo(should_notify=False)
        for reserve_address, underlying_address in reserve_to_underlying.items():
            if (properties := address_to_properties.get(reserve_address)) is None:
                name = symbol = decimals = None
            else:
                name, symbol, decimals = properties

            try:
                # calling get_or_create_evm_token along with the underlying_tokens attribute
                # will first ensure that both underlying and reserve tokens info is added,
                # then the mapping is saved. This order is necessary due to its FK relationship
                # Here we provide name, symbol and decimals since we have queried them previously
                get_or_create_evm_token(
                    userdb=node_inquirer.database,
                    evm_address=reserve_address,
                    chain_id=chain_id,
                    protocol=protocol,
                    token_kind=TokenKind.ERC20,
                    underlying_tokens=[UnderlyingToken(address=underlying_address, token_kind=TokenKind.ERC20, weight=ONE)],  # noqa: E501
                    symbol=symbol,
                    name=name,
                    decimals=decimals,
                    encounter=encounter,
                )
            except DeserializationError as e:
                log.error(
                    f'Failed to deserialize {protocol} reserve token address: '
                    f'{reserve_address} at {node_inquirer.chain_name} due to {e!s}',
                )
            except NotERC20Conformant as e:
                log.error(
                    f'Failed to add underlying token {underlying_address} for '
                    f'{reserve_address} at {node_inquirer.chain_name} due to {e!s}',
                )

    with chains_aggregator.database.conn.write_ctx() as write_cursor:
        chains_aggregator.database.set_static_cache(  # remember last task ran
            write_cursor=write_cursor,
            name=cache_key,
            value=ts_now(),
        )


def update_aave_v3_underlying_assets(chains_aggregator: ChainsAggregator) -> None:
    """Fetch the Aave V3 underlying assets and populate `underlying_tokens_list` in globaldb"""
    _update_lending_protocol_underlying_assets(
        chains_aggregator=chains_aggregator,
        providers_info=(
            (ChainID.ETHEREUM, AAVE_V3_DATA_PROVIDER_ETH),
            (ChainID.ETHEREUM, AAVE_V3_DATA_PROVIDER_ETH_OLD),
            (ChainID.ETHEREUM, LIDO_AAVE_V3_DATA_PROVIDER_ETH),
            (ChainID.ETHEREUM, ETHERFI_AAVE_V3_DATA_PROVIDER_ETH),
            (ChainID.OPTIMISM, AAVE_V3_DATA_PROVIDER_EVM),
            (ChainID.POLYGON_POS, AAVE_V3_DATA_PROVIDER_EVM),
            (ChainID.ARBITRUM_ONE, AAVE_V3_DATA_PROVIDER_EVM),
            (ChainID.BASE, AAVE_V3_DATA_PROVIDER_BASE),
            (ChainID.GNOSIS, AAVE_V3_DATA_PROVIDER_GNO),
            (ChainID.SCROLL, AAVE_V3_DATA_PROVIDER_SCRL),
        ),
        protocol=CPT_AAVE_V3,
        cache_key=DBCacheStatic.LAST_AAVE_V3_ASSETS_UPDATE,
    )


def update_spark_underlying_assets(chains_aggregator: ChainsAggregator) -> None:
    """Fetch the Spark underlying assets and populate `underlying_tokens_list` in globaldb"""
    _update_lending_protocol_underlying_assets(
        chains_aggregator=chains_aggregator,
        providers_info=(
            (ChainID.ETHEREUM, SPARK_DATA_PROVIDER_ETH),
            (ChainID.GNOSIS, SPARK_DATA_PROVIDER_GNOSIS),
        ),
        protocol=CPT_SPARK,
        cache_key=DBCacheStatic.LAST_SPARK_ASSETS_UPDATE,
    )


def maybe_detect_new_tokens(database: DBHandler) -> None:
    """Checks history events with IN direction newer than the last balance snapshot and saves
    their fungible tokens as detected. ERC721 tokens are skipped since they need an ownerOf
    check, which detect_tokens_from_decoded_events does for newly decoded events."""
    settings = CachedSettings().get_settings()
    if not settings.auto_detect_tokens:
        return

    disabled_per_chain = settings.disabled_chain_queries
    with database.conn.read_ctx() as cursor:
        tracked_accounts = {address_tuple[0] for address_tuple in cursor.execute(
            'SELECT DISTINCT account FROM blockchain_accounts;',
        )}

        last_save_time = database.get_last_balance_save_time(cursor)
        detected_tokens: defaultdict[tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, str], set[Asset]] = defaultdict(set)  # noqa: E501
        # we query the decoded history events that are the first event of each distinct
        # unignored asset for that account that happened on or after last_save_time.
        for event_data in cursor.execute(
            # events that are the earliest events of distinct assets after last_save_time
            f'SELECT {HISTORY_BASE_ENTRY_FIELDS}, {CHAIN_EVENT_FIELDS} '
            f'{EVENTS_WITH_COUNTERPARTY_JOIN} LEFT JOIN multisettings ms ON '
            'asset = ms.value AND ms.name = "ignored_asset" '
            'WHERE ms.value IS NULL AND timestamp >= ? GROUP BY asset, location_label;',
            (ts_sec_to_ms(last_save_time),),
        ):
            event = EvmEvent.deserialize_from_db(event_data[1:])
            if (
                event.location not in EVM_LOCATIONS or
                not event.asset.is_evm_token() or
                # erc721 need an ownerOf check so they are only cached by
                # detect_tokens_from_decoded_events or a full token detection
                event.asset.resolve_to_evm_token().token_kind == TokenKind.ERC721 or
                event.maybe_get_direction() != EventDirection.IN
            ):
                continue

            chain: SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE = SupportedBlockchain.from_location(event.location)  # type: ignore[assignment]  # event.location is one of EVM_LOCATIONS  # noqa: E501
            if (
                event.location_label is None or
                EVM_ADDRESS_REGEX.fullmatch(event.location_label) is None or
                event.location_label not in tracked_accounts
            ):
                log.warning(
                    f'Found invalid or non-tracked location label {event.location_label} in '
                    f'history {event=} in {event.location} while detecting new tokens. Skipping.',
                )
                continue

            if (disabled := disabled_per_chain.get(chain)) is not None and (
                len(disabled) == 0 or event.location_label in disabled
            ):
                continue

            detected_tokens[chain, event.location_label].add(event.asset)

    with (
        database.conn.read_ctx() as cursor,
        database.conn.write_ctx() as write_cursor,
    ):
        for (chain, location_label), tokens in detected_tokens.items():
            if chain == SupportedBlockchain.GNOSIS:
                token_exceptions = GNOSIS_MONERIUM_LEGACY_ADDRESSES
            elif chain == SupportedBlockchain.POLYGON_POS:
                token_exceptions = POLYGON_MONERIUM_LEGACY_ADDRESSES
            else:
                token_exceptions = set()

            old_tokens, _ = database.get_tokens_for_address(
                cursor=cursor,
                address=(address := string_to_evm_address(location_label)),
                blockchain=chain,
                token_exceptions=token_exceptions,
            )
            database.save_tokens_for_address(
                write_cursor=write_cursor,
                address=address,
                blockchain=chain,
                tokens=list(set(old_tokens or {}).union(tokens)),
            )


def _get_tracked_sender_tx_refs(
        cursor: DBCursor,
        chain_id: ChainID,
        tx_refs: set[EVMTxHash],
        tracked_accounts: set[ChecksumEvmAddress],
) -> set[EVMTxHash]:
    """Returns which of the given transactions were sent by a tracked account"""
    sent_by_tracked: set[EVMTxHash] = set()
    for chunk in get_chunks(list(tx_refs), n=500):
        sent_by_tracked.update(
            tx_hash for tx_hash, from_address in cursor.execute(
                'SELECT tx_hash, from_address FROM evm_transactions WHERE chain_id=? AND '
                f'tx_hash IN ({",".join(["?"] * len(chunk))})',
                (chain_id.serialize_for_db(), *chunk),
            ) if from_address in tracked_accounts
        )

    return sent_by_tracked


def detect_tokens_from_decoded_events(
        database: DBHandler,
        evm_inquirer: EvmNodeInquirer,
        events: Sequence[EvmEvent],
) -> None:
    """Save as detected the tokens that tracked accounts received in the given decoded events.

    This is what makes the tokens of newly decoded transactions show up in balances without
    a full token detection. Contrary to maybe_detect_new_tokens it also takes into account
    historical transactions decoded after the latest balance snapshot. To avoid caching
    spam from unsolicited airdrops, receives older than the snapshot are only considered if
    they were decoded with a counterparty or their transaction was sent by a tracked
    account. Newer receives are all considered, as maybe_detect_new_tokens did.

    This is the only automatic path caching erc721 tokens, and they are only saved if the
    account currently owns the specific token id. The tokens are added to the existing
    cache, so a failed ownership check can be retried by the next full token detection
    without having lost the previously cached tokens.
    """
    if len(events) == 0:
        return

    settings = CachedSettings().get_settings()
    if not settings.auto_detect_tokens:
        return

    chain = evm_inquirer.blockchain
    if (disabled := settings.disabled_chain_queries.get(chain)) is not None and len(disabled) == 0:
        return  # the whole chain is disabled

    with database.conn.read_ctx() as cursor:
        tracked_accounts = set(database.get_blockchain_accounts(cursor).get(chain))
        ignored_asset_ids = database.get_ignored_asset_ids(cursor)
        last_save_ts = ts_sec_to_ms(database.get_last_balance_save_time(cursor))
        candidates: defaultdict[ChecksumEvmAddress, set[str]] = defaultdict(set)
        needs_sender_check: list[tuple[ChecksumEvmAddress, str, EVMTxHash]] = []
        for event in events:
            if (
                event.location_label is None or
                (address := string_to_evm_address(event.location_label)) not in tracked_accounts or
                (disabled is not None and event.location_label in disabled) or
                event.asset.identifier in ignored_asset_ids or
                event.maybe_get_direction() != EventDirection.IN
            ):
                continue

            if event.counterparty is not None or event.timestamp >= last_save_ts:
                candidates[address].add(event.asset.identifier)
            else:
                needs_sender_check.append((address, event.asset.identifier, event.tx_ref))

        if len(needs_sender_check) != 0:
            sent_by_tracked = _get_tracked_sender_tx_refs(
                cursor=cursor,
                chain_id=evm_inquirer.chain_id,
                tx_refs={tx_ref for _, _, tx_ref in needs_sender_check},
                tracked_accounts=tracked_accounts,
            )
            for address, asset_id, tx_ref in needs_sender_check:
                if tx_ref in sent_by_tracked:
                    candidates[address].add(asset_id)

        for address, asset_ids in candidates.items():  # skip cached tokens to avoid ownerOf calls
            asset_ids.difference_update(database.get_cached_token_ids(
                cursor=cursor,
                address=address,
                chain_id=evm_inquirer.chain_id,
                token_ids=asset_ids,
            ))

    fungible_tokens: list[tuple[ChecksumEvmAddress, EvmToken]] = []
    erc721_tokens: list[tuple[ChecksumEvmAddress, EvmToken]] = []
    # sorted so the ownerOf calls batched into the multicall below have a deterministic
    # order regardless of set hash randomization
    for address, asset_id in sorted((a, x) for a, ids in candidates.items() for x in ids):
        try:
            token = EvmToken(asset_id)
        except (UnknownAsset, WrongAssetType):
            continue  # not an evm token

        if token.chain_id != evm_inquirer.chain_id or token.protocol == SPAM_PROTOCOL:
            continue

        if token.token_kind == TokenKind.ERC721:
            erc721_tokens.append((address, token))
        else:
            fungible_tokens.append((address, token))

    if len(ownership_failed := (ownership := query_owned_erc721_tokens(
        evm_inquirer=evm_inquirer,
        candidates=erc721_tokens,
    )).failed) != 0:
        log.error(
            'Failed to check the ownership of %s erc721 tokens in '
            '%s. They will be picked up by the next full token detection.',
            len(ownership_failed),
            evm_inquirer.chain_name,
        )

    tokens_per_address: defaultdict[ChecksumEvmAddress, list[EvmToken]] = defaultdict(list)
    for address, token in (*fungible_tokens, *ownership.owned):
        tokens_per_address[address].append(token)

    if len(tokens_per_address) == 0:
        return

    with database.user_write() as write_cursor:
        for address, tokens in tokens_per_address.items():
            database.add_tokens_for_address(
                write_cursor=write_cursor,
                address=address,
                blockchain=chain,
                tokens=tokens,
            )
