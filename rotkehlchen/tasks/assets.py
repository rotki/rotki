import logging
from multiprocessing.managers import RemoteError
from typing import TYPE_CHECKING

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import check_if_spam_token
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.misc import (
    LAST_AUGMENTED_SPAM_ASSETS_DETECT_KEY,
    LAST_SPAM_ASSETS_DETECT_KEY,
)
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CHAINID_TO_SUPPORTED_BLOCKCHAIN, SPAM_PROTOCOL, ChainID
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.history.events.structures.evm_event import EvmEvent


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

SYMBOL_AND_NAME_ASSETS_QUERY = (
    'SELECT C.symbol, A.name, A.identifier, B.chain FROM evm_tokens as B LEFT JOIN '
    'common_asset_details AS C ON C.identifier = B.identifier JOIN assets as A on '
    'A.identifier=B.identifier WHERE B.PROTOCOL IS NOT ? ORDER BY C.symbol'
)
MULTISEND_SPAM_THRESHOLD = 5


def _add_spam_asset(
        detected_spam_assets: list[str],
        globaldb: GlobalDBHandler,
        user_db: DBHandler,
        user_db_write_cursor: DBCursor,
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
        write_cursor=user_db_write_cursor,
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
            if check_if_spam_token(symbol=symbol, name=name) is False:
                continue

            deserialized_chain_id = ChainID.deserialize_from_db(chain_id)
            detected_spam_assets.append(identifier)
            chains_to_refresh.add(deserialized_chain_id)
            log.debug(f'Detected spam token {identifier} at chain {deserialized_chain_id}')

    if len(detected_spam_assets) == 0:
        return

    # update the user list of ignored assets
    with user_db.conn.write_ctx() as write_cursor:
        _add_spam_asset(
            detected_spam_assets=detected_spam_assets,
            globaldb=globaldb,
            user_db=user_db,
            user_db_write_cursor=write_cursor,
        )
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


def augmented_spam_detection(user_db: DBHandler) -> None:
    """
    Make a more exhaustive check looking for spam tokens. What it does is:
    1. Query the assets in the history events
    2. Filter the assets that have only receive events
    3. Check if the logs for the tx receipt has more than MULTISEND_SPAM_THRESHOLD transfers
    4. Check price using defillama as oracle

    For any asset that passes all the previous filters we mark it as spam and it is ignored.
    """
    history_db = DBHistoryEvents(user_db)
    evm_tx_db = DBEvmTx(user_db)
    inquirer = Inquirer()
    globaldb = GlobalDBHandler()
    usd_asset = A_USD.resolve_to_fiat_asset()
    chains_with_spam: set[ChainID] = set()

    spam_assets: set[str] = set()
    with user_db.conn.read_ctx() as cursor:
        cursor.execute('SELECT DISTINCT asset FROM history_events')
        for (asset_id,) in cursor:
            asset = Asset(asset_id)
            if (
                not asset.is_evm_token() or
                asset.identifier in spam_assets
            ):
                continue

            events: list['EvmEvent'] = history_db.get_history_events(
                cursor=cursor,
                filter_query=EvmEventFilterQuery.make(
                    assets=(asset,),
                    order_by_rules=[('timestamp', True)],
                ),
                has_premium=True,
                group_by_event_ids=False,
            )

            if (
                len(events) == 0 or
                not all(event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE for event in events)  # noqa: E501
            ):  # check if all the events are receive and nothing else
                continue

            if (receipt := evm_tx_db.get_receipt(
                cursor=cursor,
                tx_hash=events[0].tx_hash,
                chain_id=ChainID(events[0].location.to_chain_id()),
            )) is None:  # check if the transaction could be a multisend
                log.error(f'Could not find receipt for event {events[0].identifier=}')
                continue

            transfer_counter = 0
            for log_event in receipt.logs:  # Check if there is enough transfers to consider it spam  # noqa: E501
                if log_event.topics[0] == ERC20_OR_ERC721_TRANSFER:
                    transfer_counter += 1

                if transfer_counter >= MULTISEND_SPAM_THRESHOLD:
                    break
            else:
                continue  # not spam

            token = asset.resolve_to_evm_token()
            try:  # check if defillama has a price for the token as a last check
                price, _ = inquirer._defillama.query_current_price(
                    from_asset=token,
                    to_asset=usd_asset,
                    match_main_currency=True,
                )
            except RemoteError:
                log.error(
                    f'Failed to query defillama when doing spam detection on {asset=}. '
                    'Skipping it for now',
                )
                continue

            if price == ZERO_PRICE:
                log.info(f'Determined {asset} is a spam asset. Marking it as such.')
                spam_assets.add(asset.identifier)
                chains_with_spam.add(token.chain_id)

    with user_db.conn.write_ctx() as write_cursor:
        _add_spam_asset(
            detected_spam_assets=list(spam_assets),
            globaldb=globaldb,
            user_db=user_db,
            user_db_write_cursor=write_cursor,
        )
        write_cursor.execute(  # remember last time augmented spam detection ran
            'INSERT OR REPLACE INTO settings (name, value) VALUES (?, ?)',
            (LAST_AUGMENTED_SPAM_ASSETS_DETECT_KEY, str(ts_now())),
        )

    for chain in chains_with_spam:  # let frontend know so they refresh balances
        if chain not in CHAINID_TO_SUPPORTED_BLOCKCHAIN:
            continue

        user_db.msg_aggregator.add_message(
            message_type=WSMessageType.REFRESH_BALANCES,
            data={
                'type': 'blockchain_balances',
                'blockchain': chain.to_blockchain().serialize(),
            },
        )
