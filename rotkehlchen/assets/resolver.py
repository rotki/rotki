import logging
from typing import TYPE_CHECKING, Optional, TypeVar

from rotkehlchen.assets.types import AssetType
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.data_structures import LRUCacheLowerKey

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import (
        AssetWithNameAndType,
        AssetWithOracles,
        AssetWithSymbol,
        CryptoAsset,
        EvmToken,
        FiatAsset,
        Nft,
    )


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
T = TypeVar('T', 'FiatAsset', 'CryptoAsset', 'EvmToken', 'Nft', 'AssetWithNameAndType', 'AssetWithSymbol', 'AssetWithOracles')  # noqa: E501


class AssetResolver:
    __instance: Optional['AssetResolver'] = None
    # A cache so that the DB is not hit every time
    # the cache maps identifier -> final representation of the asset
    assets_cache: LRUCacheLowerKey['AssetWithNameAndType'] = LRUCacheLowerKey(maxsize=512)
    types_cache: LRUCacheLowerKey[AssetType] = LRUCacheLowerKey(maxsize=512)

    def __new__(cls) -> 'AssetResolver':
        """Lazily initializes AssetResolver

        It always uses the GlobalDB to resolve assets
        """
        if AssetResolver.__instance is not None:
            return AssetResolver.__instance

        AssetResolver.__instance = object.__new__(cls)
        return AssetResolver.__instance

    @staticmethod
    def clean_memory_cache(identifier: str | None = None) -> None:
        """Clean the memory cache of either a single or all assets"""
        assert AssetResolver.__instance is not None, 'when cleaning the cache instance should be set'  # noqa: E501
        if identifier is not None:
            AssetResolver.__instance.assets_cache.remove(identifier)
            AssetResolver.__instance.types_cache.remove(identifier)
        else:
            AssetResolver.__instance.assets_cache.clear()
            AssetResolver.__instance.types_cache.clear()

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

        # TODO: This is ugly here but is here to avoid a cyclic import in the Assets file
        # Couldn't find a reorg that solves this cyclic import
        from rotkehlchen.constants.assets import CONSTANT_ASSETS  # pylint: disable=import-outside-toplevel  # isort:skip
        from rotkehlchen.globaldb.handler import GlobalDBHandler  # pylint: disable=import-outside-toplevel  # isort:skip

        # If was not found in the cache try querying it in the globaldb
        try:
            asset = GlobalDBHandler.resolve_asset(identifier=identifier)
        except UnknownAsset:
            if identifier not in CONSTANT_ASSETS:
                raise

            log.debug(f'Attempt to resolve asset {identifier} using the packaged database')
            asset = GlobalDBHandler().resolve_asset_from_packaged_and_store(identifier=identifier)

        # Save it in the cache
        AssetResolver.assets_cache.add(identifier, asset)
        return asset

    @staticmethod
    def get_asset_type(identifier: str, query_packaged_db: bool = True) -> AssetType:
        if (cached_data := AssetResolver.types_cache.get(identifier)) is not None:
            return cached_data

        # TODO: This is ugly here but is here to avoid a cyclic import in the Assets file
        # Couldn't find a reorg that solves this cyclic import
        from rotkehlchen.constants.assets import CONSTANT_ASSETS  # pylint: disable=import-outside-toplevel  # isort:skip
        from rotkehlchen.globaldb.handler import GlobalDBHandler  # pylint: disable=import-outside-toplevel  # isort:skip

        try:
            asset_type = GlobalDBHandler.get_asset_type(identifier)
        except UnknownAsset:
            if identifier not in CONSTANT_ASSETS or query_packaged_db is False:
                raise

            log.debug(f'Attempt to get asset_type for {identifier} using the packaged database')
            asset = GlobalDBHandler().resolve_asset_from_packaged_and_store(identifier=identifier)
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

        # TODO: This is ugly here but is here to avoid a cyclic import in the Assets file
        # Couldn't find a reorg that solves this cyclic import
        from rotkehlchen.constants.assets import CONSTANT_ASSETS  # pylint: disable=import-outside-toplevel  # isort:skip
        from rotkehlchen.globaldb.handler import GlobalDBHandler  # pylint: disable=import-outside-toplevel  # isort:skip

        try:
            normalized_id = GlobalDBHandler.asset_id_exists(identifier)
        except UnknownAsset:
            if identifier not in CONSTANT_ASSETS or query_packaged_db is False:
                raise

            log.debug(f'Attempt to find normalized asset ID for {identifier} using the packaged database')  # noqa: E501
            normalized_id = GlobalDBHandler.asset_id_exists(identifier=identifier, use_packaged_db=True)  # noqa: E501

        return normalized_id

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

        from rotkehlchen.constants.assets import CONSTANT_ASSETS  # pylint: disable=import-outside-toplevel  # isort:skip
        from rotkehlchen.globaldb.handler import GlobalDBHandler  # pylint: disable=import-outside-toplevel  # isort:skip

        if identifier in CONSTANT_ASSETS:
            # Check if the version in the packaged globaldb is correct
            globaldb = GlobalDBHandler()
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
