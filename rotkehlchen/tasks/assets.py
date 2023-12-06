import logging
from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import check_if_spam_token
from rotkehlchen.constants.misc import LAST_SPAM_ASSETS_DETECT_KEY
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CHAINID_TO_SUPPORTED_BLOCKCHAIN, SPAM_PROTOCOL, ChainID
from rotkehlchen.utils.misc import ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

SYMBOL_AND_NAME_ASSETS_QUERY = (
    'SELECT C.symbol, A.name, A.identifier, B.chain FROM evm_tokens as B LEFT JOIN '
    'common_asset_details AS C ON C.identifier = B.identifier JOIN assets as A on '
    'A.identifier=B.identifier WHERE B.PROTOCOL IS NOT ? ORDER BY C.symbol'
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
            if check_if_spam_token(symbol=symbol, name=name) is False:
                continue

            deserialized_chain_id = ChainID.deserialize_from_db(chain_id)
            detected_spam_assets.append(identifier)
            chains_to_refresh.add(deserialized_chain_id)
            log.debug(f'Detected spam token {identifier} at chain {deserialized_chain_id}')

    if len(detected_spam_assets) == 0:
        return

    # set the spam protocol for the newly detected tokens
    with globaldb.conn.write_ctx() as write_cursor:
        query = 'UPDATE evm_tokens SET protocol=? WHERE identifier=?'
        write_cursor.executemany(
            query,
            [(SPAM_PROTOCOL, identifier) for identifier in detected_spam_assets],
        )

    # update the user list of ignored assets
    with user_db.conn.write_ctx() as write_cursor:
        for asset_id in detected_spam_assets:
            user_db.add_to_ignored_assets(write_cursor=write_cursor, asset=Asset(asset_id))

        write_cursor.execute(  # remember last time spam detection ran
            'INSERT OR REPLACE INTO settings (name, value) VALUES (?, ?)',
            (LAST_SPAM_ASSETS_DETECT_KEY, str(ts_now())),
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
