from typing import TYPE_CHECKING, Any, Optional

from polyleven import levenshtein

from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants.assets import A_ETH, A_ETH2
from rotkehlchen.constants.resolver import ChainID
from rotkehlchen.db.filtering import LevenshteinFilterQuery
from rotkehlchen.globaldb.handler import ALL_ASSETS_TABLES_QUERY, GlobalDBHandler

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor


def _search_only_nfts_levenstein(
        cursor: 'DBCursor',
        filter_query: 'LevenshteinFilterQuery',
) -> list[tuple[int, dict[str, Any]]]:
    query, bindings = filter_query.prepare('nfts')
    cursor.execute('SELECT identifier, name, collection_name FROM nfts ' + query, bindings)
    search_result: list[tuple[int, dict[str, Any]]] = []
    for entry in cursor:
        lev_dist_min = 100
        if entry[1] is not None:
            lev_dist_min = min(
                lev_dist_min,
                levenshtein(filter_query.substring_search, entry[1].casefold()),
            )
        if entry[2] is not None:
            lev_dist_min = min(
                lev_dist_min,
                levenshtein(filter_query.substring_search, entry[2].casefold()),
            )
        entry_info = {
            'identifier': entry[0],
            'name': entry[1],
            'collection_name': entry[2],
            'asset_type': AssetType.NFT.serialize(),
        }
        search_result.append((lev_dist_min, entry_info))

    return search_result


def _search_only_assets_levenstein(
        cursor: 'DBCursor',
        db: 'DBHandler',
        filter_query: 'LevenshteinFilterQuery',
) -> list[tuple[int, dict[str, Any]]]:
    search_result: list[tuple[int, dict[str, Any]]] = []
    resolved_eth = A_ETH.resolve_to_crypto_asset()
    with GlobalDBHandler().conn.read_ctx() as globaldb_cursor:
        query, bindings = filter_query.prepare('assets')
        globaldb_cursor.execute(ALL_ASSETS_TABLES_QUERY + query, bindings)
        treat_eth2_as_eth = db.get_settings(cursor).treat_eth2_as_eth
        found_eth = False
        for entry in globaldb_cursor:
            lev_dist_min = 100
            if entry[1] is not None:
                lev_dist_min = min(
                    lev_dist_min,
                    levenshtein(filter_query.substring_search, entry[1].casefold()),
                )
            if entry[2] is not None:
                lev_dist_min = min(
                    lev_dist_min,
                    levenshtein(filter_query.substring_search, entry[2].casefold()),
                )
            if treat_eth2_as_eth is True and entry[0] in (A_ETH.identifier, A_ETH2.identifier):  # noqa: E501
                if found_eth is False:
                    search_result.append((lev_dist_min, {
                        'identifier': resolved_eth.identifier,
                        'name': resolved_eth.name,
                        'symbol': resolved_eth.symbol,
                        'asset_type': AssetType.OWN_CHAIN.serialize(),
                    }))
                    found_eth = True
                continue

            entry_info = {
                'identifier': entry[0],
                'name': entry[1],
                'symbol': entry[2],
                'asset_type': AssetType.deserialize_from_db(entry[4]).serialize(),
            }
            if entry[3] is not None:
                entry_info['evm_chain'] = ChainID.deserialize_from_db(entry[3]).to_name()
            if entry[5] is not None:
                entry_info['custom_asset_type'] = entry[5]

            search_result.append((lev_dist_min, entry_info))

    return search_result


def search_assets_levenshtein(
        db: 'DBHandler',
        filter_query: 'LevenshteinFilterQuery',
        limit: Optional[int],
        search_nfts: bool,
) -> list[dict[str, Any]]:
    """Returns a list of asset details that match the search keyword using the Levenshtein distance approach."""  # noqa: E501
    search_result = []
    with db.conn.read_ctx() as cursor:
        search_result = _search_only_assets_levenstein(
            cursor=cursor,
            db=db,
            filter_query=filter_query,
        )
        if search_nfts is True:
            search_result += _search_only_nfts_levenstein(cursor=cursor, filter_query=filter_query)

    sorted_search_result = [result for _, result in sorted(search_result, key=lambda item: item[0])]  # noqa: E501
    return sorted_search_result[:limit] if limit is not None else sorted_search_result
