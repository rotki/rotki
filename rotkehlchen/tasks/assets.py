import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Final

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import Asset, UnderlyingToken
from rotkehlchen.assets.types import AssetType
from rotkehlchen.assets.utils import (
    TokenEncounterInfo,
    check_if_spam_token,
    get_or_create_evm_token,
)
from rotkehlchen.chain.base.modules.aave.v3.constants import (
    AAVE_V3_DATA_PROVIDER as AAVE_V3_DATA_PROVIDER_BASE,
)
from rotkehlchen.chain.ethereum.modules.aave.v3.constants import (
    AAVE_V3_DATA_PROVIDER as AAVE_V3_DATA_PROVIDER_ETH,
)
from rotkehlchen.chain.ethereum.utils import MULTICALL_CHUNKS
from rotkehlchen.chain.evm.constants import EVM_ADDRESS_REGEX
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE_V3
from rotkehlchen.chain.evm.decoding.aave.v3.constants import (
    AAVE_V3_DATA_PROVIDER as AAVE_V3_DATA_PROVIDER_EVM,
)
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.gnosis.modules.aave.v3.constants import (
    AAVE_V3_DATA_PROVIDER as AAVE_V3_DATA_PROVIDER_GNO,
)
from rotkehlchen.chain.scroll.modules.aave.v3.constants import (
    AAVE_V3_DATA_PROVIDER as AAVE_V3_DATA_PROVIDER_SCRL,
)
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.misc import ONE
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.constants import EVM_EVENT_FIELDS, HISTORY_BASE_ENTRY_FIELDS
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.drivers.client import DBWriterClient
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EVM_EVENT_JOIN, EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents, filter_ignore_asset_query
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import NotERC20Conformant, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import (
    globaldb_general_cache_exists,
    globaldb_get_general_cache_values,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import (
    EventDirection,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import (
    CHAINID_TO_SUPPORTED_BLOCKCHAIN,
    EVM_LOCATIONS,
    EVMLIKE_LOCATIONS,
    SPAM_PROTOCOL,
    SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE,
    CacheType,
    ChainID,
    EvmTokenKind,
    SupportedBlockchain,
)
from rotkehlchen.utils.misc import ts_now, ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.types import ChecksumEvmAddress


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

SYMBOL_AND_NAME_ASSETS_QUERY = (
    'SELECT C.symbol, A.name, A.identifier, B.chain FROM evm_tokens as B LEFT JOIN '
    'common_asset_details AS C ON C.identifier = B.identifier JOIN assets as A on '
    'A.identifier=B.identifier WHERE B.PROTOCOL IS NOT ? ORDER BY C.symbol'
)
MULTISEND_SPAM_THRESHOLD = 10  # we cover the case of multiple token rewards in the same transactions  # noqa: E501
KNOWN_FALSE_POSITIVES: Final = {
    'eip155:1/erc20:0xA0b73E1Ff0B80914AB6fe0444E65848C4C34450b',  # crypto.com CRO token
    'eip155:1/erc20:0xB63B606Ac810a52cCa15e44bB630fd42D8d1d83d',  # crypto.com
}


def _add_spam_asset(
        detected_spam_assets: list[str],
        globaldb: GlobalDBHandler,
        user_db: DBHandler,
        user_db_write_cursor: DBWriterClient,
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
    with (
        user_db.conn.read_ctx() as cursor,
        globaldb.conn.read_ctx() as globaldb_cursor,
    ):
        cursor.execute('SELECT DISTINCT asset FROM history_events')
        assets = [row[0] for row in cursor]
        # query assets marked as false positive
        false_positive_ids = set(globaldb_get_general_cache_values(
            cursor=globaldb_cursor,
            key_parts=(CacheType.SPAM_ASSET_FALSE_POSITIVE,),
        ))

        globaldb_cursor.execute(  # take only assets that are in the global DB
            f'SELECT identifier FROM assets WHERE identifier IN ({", ".join(["?"] * len(assets))}) AND type=?',  # noqa: E501
            [*assets, AssetType.EVM_TOKEN.serialize_for_db()],
        )

        for (asset_id,) in globaldb_cursor:
            if asset_id in false_positive_ids:
                continue

            asset = Asset(asset_id)
            events: list[EvmEvent] = history_db.get_history_events(
                cursor=cursor,
                filter_query=EvmEventFilterQuery.make(
                    assets=(asset,),
                    order_by_rules=[('timestamp', True)],
                    excluded_locations=list(EVMLIKE_LOCATIONS),  # exclude evm like events because they don't have EVM transactions  # noqa: E501
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

            transfer_counter: defaultdict[ChecksumEvmAddress, int] = defaultdict(int)
            # check if there is a contract that made what we consider a spam amount of transfers
            for log_event in receipt.logs:
                if log_event.topics[0] == ERC20_OR_ERC721_TRANSFER:
                    transfer_counter[log_event.address] += 1

                # check if a specific contract performed transfers above the threshold
                if any(tx_count >= MULTISEND_SPAM_THRESHOLD for tx_count in transfer_counter.values()):  # noqa: E501
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
            'INSERT OR REPLACE INTO key_value_cache (name, value) VALUES (?, ?)',
            (DBCacheStatic.LAST_AUGMENTED_SPAM_ASSETS_DETECT_KEY.value, str(ts_now())),
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


def update_owned_assets(user_db: DBHandler) -> None:
    """Wrapper to be used in async task to update owned assets"""
    with user_db.conn.read_ctx() as cursor:
        user_db.update_owned_assets_in_globaldb(cursor=cursor)

    with user_db.conn.write_ctx() as write_cursor:
        write_cursor.execute(  # remember last task ran
            'INSERT OR REPLACE INTO key_value_cache (name, value) VALUES (?, ?)',
            (DBCacheStatic.LAST_OWNED_ASSETS_UPDATE.value, str(ts_now())),
        )


def update_aave_v3_underlying_assets(chains_aggregator: 'ChainsAggregator') -> None:
    """Fetch the Aave v3 underlying assets and populate `underlying_tokens_list` in globaldb"""
    for chain_id, data_provider_address in (
        (ChainID.ETHEREUM, AAVE_V3_DATA_PROVIDER_ETH),
        (ChainID.OPTIMISM, AAVE_V3_DATA_PROVIDER_EVM),
        (ChainID.POLYGON_POS, AAVE_V3_DATA_PROVIDER_EVM),
        (ChainID.ARBITRUM_ONE, AAVE_V3_DATA_PROVIDER_EVM),
        (ChainID.BASE, AAVE_V3_DATA_PROVIDER_BASE),
        (ChainID.GNOSIS, AAVE_V3_DATA_PROVIDER_GNO),
        (ChainID.SCROLL, AAVE_V3_DATA_PROVIDER_SCRL),
    ):
        if len(chains_aggregator.accounts.get(chain_id.to_blockchain())) == 0:
            continue  # avoid querying chains without nodes connected

        node_inquirer = chains_aggregator.get_evm_manager(chain_id=chain_id).node_inquirer  # type: ignore[arg-type]  # all iterated ChainIDs are supported
        aave_data_provider = node_inquirer.contracts.contract(address=data_provider_address)
        underlying_tokens = []

        try:
            for _, token_address in aave_data_provider.call(
                node_inquirer=node_inquirer,
                method_name='getAllReservesTokens',
            ):  # get all the underlying tokens in aave v3
                try:
                    underlying_tokens.append(deserialize_evm_address(token_address))
                except DeserializationError as e:
                    log.error(f'Failed to deserialize Aave v3 underlying token address: {token_address} due to {e!s}')  # noqa: E501
                    continue

            reserve_tokens_addresses = node_inquirer.multicall(
                calls=[(  # get all the reserve tokens for each underlying token
                    aave_data_provider.address,
                    aave_data_provider.encode(
                        method_name='getReserveTokensAddresses',
                        arguments=[underlying_token],
                    ),
                ) for underlying_token in underlying_tokens],
                calls_chunk_size=4 if chain_id in {ChainID.ARBITRUM_ONE, ChainID.BASE} else MULTICALL_CHUNKS,  # arbiscan and basescan API breaks with chunk_size > 4  # noqa: E501
            )
        except RemoteError as e:
            log.error(f'Failed to query Aave v3 reserve tokens addresses due to {e!s}')
            continue

        # add the mappings of underlying tokens to the globaldb
        for underlying_idx, underlying_token_address in enumerate(underlying_tokens):
            for decoded_reserve_token_address in aave_data_provider.decode(
                method_name='getReserveTokensAddresses',
                arguments=[underlying_token_address],
                result=reserve_tokens_addresses[underlying_idx],
            ):
                try:
                    # calling get_or_create_evm_token along with the underlying_tokens attribute
                    # will first ensure that both underlying and reserve tokens info is added,
                    # then the mapping is saved. This order is necessary due to its FK relationship
                    decoded_reserve_token = get_or_create_evm_token(
                        evm_inquirer=node_inquirer,
                        userdb=node_inquirer.database,
                        evm_address=deserialize_evm_address(decoded_reserve_token_address),
                        chain_id=chain_id,
                        protocol=CPT_AAVE_V3,
                        token_kind=EvmTokenKind.ERC20,
                        underlying_tokens=[UnderlyingToken(
                            address=underlying_token_address,
                            token_kind=EvmTokenKind.ERC20,
                            weight=ONE,
                        )],
                        encounter=TokenEncounterInfo(should_notify=False),
                    )
                except DeserializationError as e:
                    log.error(
                        'Failed to deserialize Aave v3 reserve token address: '
                        f'{decoded_reserve_token_address} due to {e!s}',
                    )
                except NotERC20Conformant as e:
                    log.error(
                        f'Failed to add underlying token {underlying_token_address} for '
                        f'{decoded_reserve_token.identifier} due to {e!s}',
                    )

    with chains_aggregator.database.conn.write_ctx() as write_cursor:
        chains_aggregator.database.set_static_cache(  # remember last task ran
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_AAVE_V3_ASSETS_UPDATE,
            value=ts_now(),
        )


def maybe_detect_new_tokens(database: 'DBHandler') -> None:
    """Checks newly found history events with IN direction and saves their assets as detected."""
    if not CachedSettings().get_settings().auto_detect_tokens:
        return

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
            f'SELECT {HISTORY_BASE_ENTRY_FIELDS}, '
            f'{EVM_EVENT_FIELDS} {EVM_EVENT_JOIN} {filter_ignore_asset_query()} '
            'AND timestamp >= ? GROUP BY asset, location_label;',
            (ts_sec_to_ms(last_save_time),),
        ):
            event = EvmEvent.deserialize_from_db(event_data[1:])
            if (
                event.location not in EVM_LOCATIONS or
                not event.asset.is_evm_token() or
                event.maybe_get_direction() != EventDirection.IN
            ):
                continue

            chain: SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE = SupportedBlockchain.from_location(event.location)  # type: ignore[arg-type,assignment]  # event.location is one of EVM_LOCATIONS  # noqa: E501
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

            detected_tokens[chain, event.location_label].add(event.asset)

    with (
        database.conn.read_ctx() as cursor,
        database.conn.write_ctx() as write_cursor,
    ):
        for (chain, location_label), tokens in detected_tokens.items():
            old_tokens, _ = database.get_tokens_for_address(
                cursor=cursor,
                address=(address := string_to_evm_address(location_label)),
                blockchain=chain,
            )
            database.save_tokens_for_address(
                write_cursor=write_cursor,
                address=address,
                blockchain=chain,
                tokens=list(set(old_tokens or {}).union(tokens)),
            )
