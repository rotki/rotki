import logging
from typing import TYPE_CHECKING, TypeVar

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
        HyperliquidToken,
        Nft,
        SolanaToken,
    )
    from rotkehlchen.assets.types import AssetType
    from rotkehlchen.globaldb.handler import GlobalDBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
T = TypeVar('T', 'FiatAsset', 'CryptoAsset', 'EvmToken', 'Nft', 'SolanaToken', 'HyperliquidToken', 'AssetWithNameAndType', 'AssetWithSymbol', 'AssetWithOracles')  # noqa: E501


class AssetResolver:
    __instance: AssetResolver | None = None
    _globaldb: GlobalDBHandler
    _constant_assets: set[Asset]
    # A cache so that the DB is not hit every time
    # the cache maps identifier -> final representation of the asset
    assets_cache: LRUCacheLowerKey[AssetWithNameAndType] = LRUCacheLowerKey(maxsize=512)
    types_cache: LRUCacheLowerKey[AssetType] = LRUCacheLowerKey(maxsize=512)
    # Maps asset identifier -> collection main_asset identifier (or None if not in a collection).
    # None is a valid cached value so presence must be tested with `identifier.lower() in cache`.
    collection_main_asset_cache: LRUCacheLowerKey[str | None] = LRUCacheLowerKey(maxsize=512)
    # Maps asset identifier -> its normalized identifier for existence checks. Lets
    # check_existence avoid a globaldb query for every event row during deserialization.
    existence_cache: LRUCacheLowerKey[str] = LRUCacheLowerKey(maxsize=512)
    # Bumped on every clean_memory_cache. The resolution methods snapshot it before
    # querying the DB and skip the cache write-back if it changed in the meantime, so
    # a clean issued for an edited/deleted asset while a resolution is in flight
    # cannot be resurrected by that resolution's stale result. Class-wide instead of
    # per-identifier: the cost of a false positive is only one uncached call. Same
    # pattern as CacheableMixIn.cache_flush_generation.
    cache_clean_generation = 0

    def __new__(  # noqa: PYI034 # singleton pattern should not get Self
            cls,
            globaldb: GlobalDBHandler | None = None,
            constant_assets: set[Asset] | None = None,
    ) -> AssetResolver:
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
    def _may_cache(clean_generation: int) -> bool:
        """Whether a resolution result queried from the global DB may be cached.

        Not the case if the caches were cleaned after `clean_generation` was
        snapshotted (the result may predate the edit/deletion that triggered the
        clean), nor while any write transaction or savepoint stack is open on the
        global DB connection: asset editors clean the caches before committing so
        a concurrent resolution would re-cache the pre-commit state, and the
        writing task itself resolves its own yet-uncommitted data which must not
        become visible to others through the cache.
        """
        conn = AssetResolver._globaldb.conn
        return (
            AssetResolver.cache_clean_generation == clean_generation and
            conn.write_task_ident is None and
            conn.savepoint_task_ident is None
        )

    @staticmethod
    def clean_memory_cache(identifier: str | None = None) -> None:
        """Clean the memory cache of either a single or all assets"""
        assert AssetResolver.__instance is not None, 'when cleaning the cache instance should be set'  # noqa: E501
        AssetResolver.cache_clean_generation += 1  # before the removals, so in-flight resolutions always notice  # noqa: E501
        if identifier is not None:
            AssetResolver.__instance.assets_cache.remove(identifier)
            AssetResolver.__instance.types_cache.remove(identifier)
            AssetResolver.__instance.collection_main_asset_cache.remove(identifier)
            AssetResolver.__instance.existence_cache.remove(identifier)
        else:
            AssetResolver.__instance.assets_cache.clear()
            AssetResolver.__instance.types_cache.clear()
            AssetResolver.__instance.collection_main_asset_cache.clear()
            AssetResolver.__instance.existence_cache.clear()

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

        clean_generation = AssetResolver.cache_clean_generation
        main_asset = AssetResolver._globaldb.get_collection_main_asset(identifier)
        if AssetResolver._may_cache(clean_generation):
            cache.add(identifier, main_asset)
        return main_asset

    @staticmethod
    def get_collection_main_assets(identifiers: set[str]) -> dict[str, str]:
        """Return collection main assets for identifiers in bulk, using the shared cache."""
        if len(identifiers) == 0:
            return {}

        cache = AssetResolver.collection_main_asset_cache
        main_assets, to_query = {}, set()
        for identifier in identifiers:
            if identifier.lower() in cache:
                if (main_asset := cache.get(identifier)) is not None:
                    main_assets[identifier] = main_asset
            else:
                to_query.add(identifier)

        if len(to_query) == 0:
            return main_assets

        clean_generation = AssetResolver.cache_clean_generation
        queried_main_assets = AssetResolver._globaldb.get_collection_main_assets(to_query)
        queried_by_lower = {
            identifier.lower(): main_asset
            for identifier, main_asset in queried_main_assets.items()
        }
        for identifier in to_query:
            main_asset = queried_by_lower.get(identifier.lower())
            if main_asset is not None:
                main_assets[identifier] = main_asset
            if AssetResolver._may_cache(clean_generation):
                cache.add(identifier, main_asset)

        return main_assets

    @staticmethod
    def resolve_asset(identifier: str) -> AssetWithNameAndType:
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
        clean_generation = AssetResolver.cache_clean_generation
        try:
            asset = AssetResolver._globaldb.resolve_asset(identifier=identifier)
        except UnknownAsset:
            if identifier not in AssetResolver._constant_assets:
                raise

            log.debug(f'Attempt to resolve asset {identifier} using the packaged database')
            asset = AssetResolver._globaldb.resolve_asset_from_packaged_and_store(
                identifier=identifier,
            )

        if AssetResolver._may_cache(clean_generation):
            AssetResolver.assets_cache.add(identifier, asset)
        return asset

    @staticmethod
    def get_asset_type(identifier: str, query_packaged_db: bool = True) -> AssetType:
        if (cached_data := AssetResolver.types_cache.get(identifier)) is not None:
            return cached_data

        clean_generation = AssetResolver.cache_clean_generation
        # If the asset was already fully resolved its type is known, so reuse it
        # instead of issuing a fresh `SELECT type` query against the globaldb.
        if (resolved := AssetResolver.assets_cache.get(identifier)) is not None:
            if AssetResolver._may_cache(clean_generation):
                AssetResolver.types_cache.add(identifier, resolved.asset_type)
            return resolved.asset_type

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
        if AssetResolver._may_cache(clean_generation):
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
        if (normalized_id := AssetResolver.existence_cache.get(identifier)) is not None:
            return normalized_id

        clean_generation = AssetResolver.cache_clean_generation
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

        if AssetResolver._may_cache(clean_generation):
            AssetResolver.existence_cache.add(identifier, normalized_id)
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
            if (normalized_id := AssetResolver.existence_cache.get(identifier)) is not None:
                normalized_map[identifier] = normalized_id
                continue
            to_check.add(identifier)

        clean_generation = AssetResolver.cache_clean_generation
        found_by_lower: dict[str, str] = {}
        if len(to_check) != 0:
            with AssetResolver._globaldb.conn.read_ctx() as cursor:
                for chunk in get_chunks(list(to_check), n=500):
                    placeholders = ','.join(['?'] * len(chunk))
                    cursor.execute(
                        f'SELECT identifier FROM assets WHERE identifier IN ({placeholders})',
                        tuple(chunk),
                    )
                    found_by_lower.update((row[0].lower(), row[0]) for row in cursor)

        found_ids = {
            identifier
            for identifier in to_check
            if identifier.lower() in found_by_lower
        }
        normalized_map.update({
            identifier: found_by_lower[identifier.lower()]
            for identifier in found_ids
        })
        if AssetResolver._may_cache(clean_generation):
            for identifier in found_ids:
                AssetResolver.existence_cache.add(identifier, normalized_map[identifier])

        if len(missing_ids := to_check - found_ids) == 0:
            return normalized_map, set()

        if query_packaged_db is False:
            return normalized_map, missing_ids

        missing_constant = {identifier for identifier in missing_ids if identifier in AssetResolver._constant_assets}  # noqa: E501
        missing_non_constant = missing_ids - missing_constant
        packaged_by_lower: dict[str, str] = {}
        if len(missing_constant) != 0:
            with AssetResolver._globaldb.packaged_db_conn().read_ctx() as cursor:
                for chunk in get_chunks(list(missing_constant), n=500):
                    placeholders = ','.join(['?'] * len(chunk))
                    cursor.execute(
                        f'SELECT identifier FROM assets WHERE identifier IN ({placeholders})',
                        tuple(chunk),
                    )
                    packaged_by_lower.update((row[0].lower(), row[0]) for row in cursor)

        packaged_found = {
            identifier
            for identifier in missing_constant
            if identifier.lower() in packaged_by_lower
        }
        normalized_map.update({
            identifier: packaged_by_lower[identifier.lower()]
            for identifier in packaged_found
        })
        if AssetResolver._may_cache(clean_generation):
            for identifier in packaged_found:
                AssetResolver.existence_cache.add(identifier, normalized_map[identifier])
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
            clean_generation = AssetResolver.cache_clean_generation
            packaged_asset = globaldb.resolve_asset(identifier=identifier, use_packaged_db=True)
            if isinstance(packaged_asset, expected_type):  # it's what was requested. So fix local global db  # noqa: E501
                resolved_asset = globaldb.resolve_asset_from_packaged_and_store(identifier=identifier)  # noqa: E501
                if AssetResolver._may_cache(clean_generation):
                    AssetResolver.assets_cache.add(identifier, resolved_asset)
                if isinstance(resolved_asset, expected_type) is True:
                    # resolve_asset returns Asset, but we already narrow type with the if check above  # noqa: E501
                    return resolved_asset  # type: ignore

        raise WrongAssetType(
            identifier=identifier,
            expected_type=expected_type,
            real_type=type(resolved_asset),
        )
