import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.globaldb.utils import set_token_spam_protocol
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SPAM_PROTOCOL, ChainID, TokenKind

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


MISSING_NAME_SPAM_TOKEN = 'Autodetected spam token'
MISSING_SYMBOL_SPAM_TOKEN = 'SPAM-TOKEN'


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


def check_token_impersonates_base_currency(token: 'EvmToken', native_token_symbol: str) -> None:
    """
    Mark a token as spam when it appears to impersonate the chain's native
    base currency. When triggered, this function sets the token's protocol to spam.
    """
    if (
        token.protocol != SPAM_PROTOCOL and
        token.symbol == native_token_symbol and
        token.started is None  # this is to prevent flaging a token that we have added since the started we are the only ones setting it.  # noqa: E501
    ):
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            set_token_spam_protocol(
                write_cursor=write_cursor,
                token=token,
                is_spam=True,
            )
        AssetResolver.clean_memory_cache(token.identifier)
        log.debug(f'Flagged {token} as spam trying to impersonate {native_token_symbol}')
