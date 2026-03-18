import logging
from typing import TYPE_CHECKING, Optional, TypeVar

from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants.misc import NFT_DIRECTIVE
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.data_structures import LRUCacheLowerKey
from rotkehlchen.utils.misc import get_chunks

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import (
        Asset,
        AssetWithNameAndType,
        AssetWithOracles,
        AssetWithSymbol,
        CryptoAsset,
        EvmToken,
        FiatAsset,
        Nft,
        SolanaToken,
    )
    from rotkehlchen.globaldb.handler import GlobalDBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
T = TypeVar('T', 'FiatAsset', 'CryptoAsset', 'EvmToken', 'Nft', 'SolanaToken', 'AssetWithNameAndType', 'AssetWithSymbol', 'AssetWithOracles')  # noqa: E501


class AssetResolver:
    __instance: Optional['AssetResolver'] = None
    _globaldb: 'GlobalDBHandler'
    _constant_assets: set['Asset']
    # A cache so that the DB is not hit every time
    # the cache maps identifier -> final representation of the asset
    assets_cache: LRUCacheLowerKey['AssetWithNameAndType'] = LRUCacheLowerKey(maxsize=512)
    types_cache: LRUCacheLowerKey[AssetType] = LRUCacheLowerKey(maxsize=512)
    # Maps asset identifier -> collection main_asset identifier (or None if not in a collection).
    # None is a valid cached value so presence must be tested with `identifier.lower() in cache`.
    collection_main_asset_cache: LRUCacheLowerKey[str | None] = LRUCacheLowerKey(maxsize=512)

    def __new__(  # noqa: PYI034 # singleton pattern should not get Self
            cls,
            globaldb: 'GlobalDBHandler | None' = None,
            constant_assets: set['Asset'] | None = None,
    ) -> 'AssetResolver':
        """Lazily initializes AssetResolver

        It always uses the GlobalDB to resolve assets
        """
        if AssetResolver.__instance is not None:
            return AssetResolver.__instance

        assert globaldb is not None
        assert constant_assets is not None
        AssetResolver.__instance = object.__new__(cls)
        AssetResolver._globaldb = globaldb
        AssetResolver._constant_assets = constant_assets
        return AssetResolver.__instance

    @staticmethod
    def clean_memory_cache(identifier: str | None = None) -> None:
        """Clean the memory cache of either a single or all assets"""
        assert AssetResolver.__instance is not None, 'when cleaning the cache instance should be set'  # noqa: E501
        if identifier is not None:
            AssetResolver.__instance.assets_cache.remove(identifier)
            AssetResolver.__instance.types_cache.remove(identifier)
            AssetResolver.__instance.collection_main_asset_cache.remove(identifier)
        else:
            AssetResolver.__instance.assets_cache.clear()
            AssetResolver.__instance.types_cache.clear()
            AssetResolver.__instance.collection_main_asset_cache.clear()

    @staticmethod
    def get_collection_main_asset(identifier: str) -> str | None:
        """Return the main asset identifier for the collection that contains identifier.

        Returns None if identifier is not a member of any collection.
        Results are cached; None (no collection) is also a valid cached value so
        presence is checked with ``identifier.lower() in cache`` before calling .get().
        """
        cache = AssetResolver.collection_main_asset_cache
        if identifier.lower() in cache:
            return cache.get(identifier)

        main_asset = AssetResolver._globaldb.get_collection_main_asset(identifier)
        cache.add(identifier, main_asset)
        return main_asset

    @staticmethod
    def resolve_asset(identifier: str) -> 'AssetWithNameAndType':
        """
        Get all asset data for a valid asset identifier. May return any valid subclass of the
        Asset class.

        Thanks to querying the DB the resolved asset will have the normalized
        asset identifier. So say if you pass 'eTh' the returned asset id will be 'ETH'

        May raise:
        - UnknownAsset
        - WrongAssetType
        """
        if (cached_data := AssetResolver.assets_cache.get(identifier)) is not None:
            return cached_data

        # If was not found in the cache try querying it in the globaldb
        try:
            asset = AssetResolver._globaldb.resolve_asset(identifier=identifier)
        except UnknownAsset:
            if identifier not in AssetResolver._constant_assets:
                raise

            log.debug(f'Attempt to resolve asset {identifier} using the packaged database')
            asset = AssetResolver._globaldb.resolve_asset_from_packaged_and_store(
                identifier=identifier,
            )

        # Save it in the cache
        AssetResolver.assets_cache.add(identifier, asset)
        return asset

    @staticmethod
    def get_asset_type(identifier: str, query_packaged_db: bool = True) -> AssetType:
        if (cached_data := AssetResolver.types_cache.get(identifier)) is not None:
            return cached_data

        try:
            asset_type = AssetResolver._globaldb.get_asset_type(identifier)
        except UnknownAsset:
            if identifier not in AssetResolver._constant_assets or query_packaged_db is False:
                raise

            log.debug(f'Attempt to get asset_type for {identifier} using the packaged database')
            asset = AssetResolver._globaldb.resolve_asset_from_packaged_and_store(
                identifier=identifier,
            )
            asset_type = asset.asset_type
        AssetResolver.types_cache.add(identifier, asset_type)
        return asset_type

    @staticmethod
    def check_existence(identifier: str, query_packaged_db: bool = True) -> str:
        """Check that an asset with the given identifier exists and return normalized identifier

        For example if 'eTh' is given here then 'ETH' should be returned.

        May raise:
        - UnknownAsset: If asset identifier does not exist.
        """
        if (cached_data := AssetResolver.assets_cache.get(identifier)) is not None:
            return cached_data.identifier

        try:
            normalized_id = AssetResolver._globaldb.asset_id_exists(identifier)
        except UnknownAsset:
            if identifier not in AssetResolver._constant_assets or query_packaged_db is False:
                raise

            log.debug(f'Attempt to find normalized asset ID for {identifier} using the packaged database')  # noqa: E501
            normalized_id = AssetResolver._globaldb.asset_id_exists(
                identifier=identifier,
                use_packaged_db=True,
            )

        return normalized_id

    @staticmethod
    def bulk_check_existence(
            identifiers: set[str],
            query_packaged_db: bool = True,
    ) -> tuple[dict[str, str], set[str]]:
        """Check identifiers in bulk and return normalized ids and unknown ids."""
        if len(identifiers) == 0:
            return {}, set()

        normalized_map: dict[str, str] = {}
        to_check = set()
        for identifier in identifiers:
            if identifier.startswith(NFT_DIRECTIVE):
                normalized_map[identifier] = identifier
                continue
            if (cached_data := AssetResolver.assets_cache.get(identifier)) is not None:
                normalized_map[identifier] = cached_data.identifier
                continue
            to_check.add(identifier)

        found_ids: set[str] = set()
        if len(to_check) != 0:
            with AssetResolver._globaldb.conn.read_ctx() as cursor:
                for chunk in get_chunks(list(to_check), n=500):
                    placeholders = ','.join(['?'] * len(chunk))
                    cursor.execute(
                        f'SELECT identifier FROM assets WHERE identifier IN ({placeholders})',
                        tuple(chunk),
                    )
                    found_ids.update(row[0] for row in cursor)

        normalized_map.update({identifier: identifier for identifier in found_ids})

        if len(missing_ids := to_check - found_ids) == 0:
            return normalized_map, set()

        if query_packaged_db is False:
            return normalized_map, missing_ids

        missing_constant = {identifier for identifier in missing_ids if identifier in AssetResolver._constant_assets}  # noqa: E501
        missing_non_constant = missing_ids - missing_constant
        packaged_found: set[str] = set()
        if len(missing_constant) != 0:
            with AssetResolver._globaldb.packaged_db_conn().read_ctx() as cursor:
                for chunk in get_chunks(list(missing_constant), n=500):
                    placeholders = ','.join(['?'] * len(chunk))
                    cursor.execute(
                        f'SELECT identifier FROM assets WHERE identifier IN ({placeholders})',
                        tuple(chunk),
                    )
                    packaged_found.update(row[0] for row in cursor)

        normalized_map.update({identifier: identifier for identifier in packaged_found})
        unknown_ids = missing_non_constant | (missing_constant - packaged_found)
        return normalized_map, unknown_ids

    @staticmethod
    def resolve_asset_to_class(identifier: str, expected_type: type[T]) -> T:
        """
        Try to resolve an identifier to the Asset subclass defined in expected_type.

        Whenever `WrongAssetType` is encountered for an asset present in `CONSTANT_ASSETS`
        we use the packaged global db to resolve the asset.

        May raise:
        - WrongAssetType: if the asset is resolved but the class is not the expected one.
        - UnknownAsset: if the asset was not found in the database.
        """
        resolved_asset = AssetResolver.resolve_asset(identifier=identifier)
        if isinstance(resolved_asset, expected_type) is True:
            # resolve_asset returns Asset, but we already narrow type with the if check above
            return resolved_asset  # type: ignore

        if identifier in AssetResolver._constant_assets:
            # Check if the version in the packaged globaldb is correct
            globaldb = AssetResolver._globaldb
            packaged_asset = globaldb.resolve_asset(identifier=identifier, use_packaged_db=True)
            if isinstance(packaged_asset, expected_type):  # it's what was requested. So fix local global db  # noqa: E501
                resolved_asset = globaldb.resolve_asset_from_packaged_and_store(identifier=identifier)  # noqa: E501
                AssetResolver.assets_cache.add(identifier, resolved_asset)
                if isinstance(resolved_asset, expected_type) is True:
                    # resolve_asset returns Asset, but we already narrow type with the if check above  # noqa: E501
                    return resolved_asset  # type: ignore

        raise WrongAssetType(
            identifier=identifier,
            expected_type=expected_type,
            real_type=type(resolved_asset),
        )
