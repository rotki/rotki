import logging
from typing import TYPE_CHECKING, Any, Final

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import globaldb_general_cache_exists
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.globaldb.utils import set_token_spam_protocol
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SPAM_PROTOCOL, CacheType, ChainID, TokenKind
from rotkehlchen.utils.data_structures import LRUCacheWithRemove, LRUSetCache

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import CryptoAsset
    from rotkehlchen.db.dbhandler import DBCursor, DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Mapping of dangerous token symbols to their collection IDs in globaldb
DANGEROUS_TOKEN_SYMBOLS: Final = {'USDC': 36, 'USDT': 37}
MISSING_NAME_SPAM_TOKEN = 'Autodetected spam token'
MISSING_SYMBOL_SPAM_TOKEN = 'SPAM-TOKEN'

_DANGEROUS_COLLECTION_MEMBERS: dict[int, set[str]] = {}  # members in the collections of DANGEROUS_TOKEN_SYMBOLS. Maps collection id to set of assets in the collection.  # noqa: E501
_IMPERSONATION_CHECKED_TOKENS: LRUSetCache[str] = LRUSetCache(maxsize=256)  # avoid checking the same token multiple times  # noqa: E501
_FALSE_POSITIVE_CACHE: LRUCacheWithRemove[str, bool] = LRUCacheWithRemove(maxsize=256)  # cache the false positives marked by the user  # noqa: E501


def _save_or_update_spam_assets(
        db: 'DBHandler',
        assets_info: list[dict[str, Any]],
) -> set[Asset]:
    """
    Generate a set of assets that can be ignored using the list of spam
    assets assets_info.

    This function doesn't make any external query.
    """
    tokens_to_ignore = set()
    # Try to add custom list
    for info in assets_info:
        chain_name = info.get('chain')  # use name since in the future we may have non-EVM chains
        try:
            chain = ChainID.deserialize_from_name(chain_name) if chain_name is not None else ChainID.ETHEREUM  # noqa: E501
        except DeserializationError:
            log.error(f'Got unexpected chain name {chain_name} when deserializing spam asset data: {assets_info}')  # noqa: E501
            continue

        evm_token = EvmToken.initialize(
            address=info['address'],
            chain_id=chain,
            token_kind=TokenKind.ERC20,
            name=info.get('name', MISSING_NAME_SPAM_TOKEN),
            decimals=info.get('decimals', 18),
            symbol=info.get('symbol', MISSING_SYMBOL_SPAM_TOKEN),
            protocol=SPAM_PROTOCOL,
            underlying_tokens=None,
        )

        try:
            evm_token.check_existence()
        except UnknownAsset:  # token does not exist
            GlobalDBHandler.add_asset(evm_token)
            # add the asset to the asset table in the user's db
            with db.user_write() as cursor:
                db.add_asset_identifiers(cursor, [evm_token.identifier])
        else:  # token exists, make sure it has spam protocol set
            db_evm_token = EvmToken(evm_token.identifier)
            if db_evm_token.protocol != SPAM_PROTOCOL:
                GlobalDBHandler.edit_evm_token(entry=evm_token)
        # save the asset instead of the EvmToken as we don't need all the extra information later
        tokens_to_ignore.add(Asset(evm_token.identifier))

    return tokens_to_ignore


def update_spam_assets(db: 'DBHandler', assets_info: list[dict[str, Any]]) -> int:
    """
    Update the list of ignored assets using query_token_spam_list and avoiding
    the addition of duplicates. It returns the amount of assets that were added
    to the ignore list
    """
    spam_tokens = _save_or_update_spam_assets(db=db, assets_info=assets_info)
    # order matters here. Make sure ignored_assets are queried after spam tokens creation
    # since it's possible for a token to exist in ignored assets but not global DB.
    # and in that case query_token_spam_list add it to the global DB
    with db.conn.read_ctx() as cursor:
        ignored_asset_ids = db.get_ignored_asset_ids(cursor)

    with db.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT OR IGNORE INTO multisettings(name, value) VALUES(?, ?)',
            [('ignored_asset', x.identifier) for x in spam_tokens if x.identifier not in ignored_asset_ids],  # noqa: E501
        )
        return write_cursor.rowcount


def _get_dangerous_token_collection_members(
        cursor: 'DBCursor',
        collection_id: int,
) -> set[str]:
    """
    Efficiently fetch all assets in a dangerous token collection for a specific chain.
    Returns a set of asset identifiers that belong to the collection.
    Uses a single query to get all members of the collection.
    """
    try:
        cursor.execute(
            'SELECT asset FROM multiasset_mappings WHERE collection_id=?;',
            (collection_id,),
        )
        return {row[0] for row in cursor}
    except sqlcipher.OperationalError as e:  # pylint: disable=no-member
        log.warning(f'Failed to query collection {collection_id} members: {e}')
        return set()


def check_token_impersonates_dangerous_tokens(
        token: 'EvmToken',
        native_token: 'CryptoAsset',
) -> None:
    """
    Mark a token as spam when it appears to impersonate well-known tokens like the native currency
    (ETH, POL, xDAI) or stablecoins (USDC, USDT).

    For native tokens: flags if symbol matches but identifier doesn't match the real native asset.
    For stablecoins: flags if symbol matches but not in the known collection (whitelist).

    This function:
    1. Checks native token impersonation: symbol matches but identifier differs
    2. Checks stablecoin impersonation: symbol in known collections but not whitelisted
    3. Respects the whitelist from the SPAM_ASSET_FALSE_POSITIVE cache
    """
    if token.protocol == SPAM_PROTOCOL or token.started is not None:
        return

    if token.identifier in _IMPERSONATION_CHECKED_TOKENS:
        return

    globaldb = GlobalDBHandler()
    # Check native token impersonation (e.g., POL token that's not the real POL)
    impersonated_symbol: str | None = None
    if token.symbol == native_token.symbol and token.identifier != native_token.identifier:
        impersonated_symbol = native_token.symbol
    elif (collection_id := DANGEROUS_TOKEN_SYMBOLS.get(token.symbol)) is not None:
        if (known_tokens := _DANGEROUS_COLLECTION_MEMBERS.get(collection_id)) is None:
            with globaldb.conn.read_ctx() as read_cursor:
                known_tokens = _get_dangerous_token_collection_members(read_cursor, collection_id)
            _DANGEROUS_COLLECTION_MEMBERS[collection_id] = known_tokens

        # Check if this token is in the known collection (whitelist)
        if token.identifier not in known_tokens:
            impersonated_symbol = token.symbol

    if impersonated_symbol is not None:
        if (is_false_positive := _FALSE_POSITIVE_CACHE.get(token.identifier)) is None:
            with globaldb.conn.read_ctx() as read_cursor:
                is_false_positive = globaldb_general_cache_exists(
                    cursor=read_cursor,
                    key_parts=(CacheType.SPAM_ASSET_FALSE_POSITIVE,),
                    value=token.identifier,
                )
            _FALSE_POSITIVE_CACHE.add(token.identifier, is_false_positive)

        if is_false_positive:
            _IMPERSONATION_CHECKED_TOKENS.add(token.identifier)
            return

        with globaldb.conn.write_ctx() as write_cursor:
            set_token_spam_protocol(
                write_cursor=write_cursor,
                token=token,
                is_spam=True,
            )

        log.debug(f'Flagged {token} as spam trying to impersonate {impersonated_symbol}')
    _IMPERSONATION_CHECKED_TOKENS.add(token.identifier)
