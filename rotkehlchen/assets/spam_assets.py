import logging
from typing import TYPE_CHECKING, Any


from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.types import AssetType
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SPAM_PROTOCOL, ChainID, EvmTokenKind

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
        chain_id = info.get('chain')
        chain = ChainID.deserialize(chain_id) if chain_id is not None else ChainID.ETHEREUM

        evm_token = EvmToken.initialize(
            address=info['address'],
            chain_id=chain,
            token_kind=EvmTokenKind.ERC20,
            name=info.get('name', MISSING_NAME_SPAM_TOKEN),
            decimals=info.get('decimals', 18),
            symbol=info.get('symbol', MISSING_SYMBOL_SPAM_TOKEN),
            protocol=SPAM_PROTOCOL,
            underlying_tokens=None,
        )

        try:
            evm_token.check_existence()
        except UnknownAsset:  # token does not exist
            GlobalDBHandler().add_asset(
                asset_id=evm_token.identifier,
                asset_type=AssetType.EVM_TOKEN,
                data=evm_token,
            )
            # add the asset to the asset table in the user's db
            with db.user_write() as cursor:
                db.add_asset_identifiers(cursor, [evm_token.identifier])
        else:  # token exists, make sure it has spam protocol set
            db_evm_token = EvmToken(evm_token.identifier)
            if db_evm_token.protocol != SPAM_PROTOCOL:
                GlobalDBHandler().edit_evm_token(entry=evm_token)
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
        ignored_assets = {asset.identifier for asset in db.get_ignored_assets(cursor)}
    assets_added = 0
    for token in spam_tokens:
        if token.identifier in ignored_assets:
            continue

        with db.user_write() as write_cursor:
            db.add_to_ignored_assets(write_cursor=write_cursor, asset=token)
        assets_added += 1
    return assets_added
