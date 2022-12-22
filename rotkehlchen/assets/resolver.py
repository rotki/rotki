import logging
from typing import TYPE_CHECKING, Optional, TypeVar

from rotkehlchen.assets.types import AssetType
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.data_structures import LRUCacheWithRemove

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
    )


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
T = TypeVar('T', 'FiatAsset', 'CryptoAsset', 'EvmToken', 'Nft', 'AssetWithNameAndType', 'AssetWithSymbol', 'AssetWithOracles')  # noqa: E501


class AssetResolver():
    __instance: Optional['AssetResolver'] = None
    # A cache so that the DB is not hit every time
    # the cache maps identifier -> final representation of the asset
    assets_cache: LRUCacheWithRemove['Asset'] = LRUCacheWithRemove(maxsize=512)
    types_cache: LRUCacheWithRemove[AssetType] = LRUCacheWithRemove(maxsize=512)

    def __new__(cls) -> 'AssetResolver':
        """Lazily initializes AssetResolver

        It always uses the GlobalDB to resolve assets
        """
        if AssetResolver.__instance is not None:
            return AssetResolver.__instance

        AssetResolver.__instance = object.__new__(cls)
        return AssetResolver.__instance

    @staticmethod
    def clean_memory_cache(identifier: Optional[str] = None) -> None:
        """Clean the memory cache of either a single or all assets"""
        assert AssetResolver.__instance is not None, 'when cleaning the cache instance should be set'  # noqa: E501
        if identifier is not None:
            AssetResolver.__instance.assets_cache.remove(identifier)
            AssetResolver.__instance.types_cache.remove(identifier)
        else:
            AssetResolver.__instance.assets_cache.clear()
            AssetResolver.__instance.types_cache.clear()

    @staticmethod
    def resolve_asset(identifier: str) -> 'Asset':
        """
        Get all asset data for a valid asset identifier. May return any valid subclass of the
        Asset class.

        May raise:
        - UnknownAsset
        - WrongAssetType
        """
        # TODO: This is ugly here but is here to avoid a cyclic import in the Assets file
        # Couldn't find a reorg that solves this cyclic import
        from rotkehlchen.constants.assets import CONSTANT_ASSETS  # pylint: disable=import-outside-toplevel  # isort:skip  # noqa: E501
        from rotkehlchen.globaldb.handler import GlobalDBHandler  # pylint: disable=import-outside-toplevel  # isort:skip  # noqa: E501

        instance = AssetResolver()
        cached_data = instance.assets_cache.get(identifier)
        if cached_data is not None:
            return cached_data

        # If was not found in the cache try querying it in the globaldb
        try:
            asset = GlobalDBHandler().resolve_asset(identifier=identifier)
        # `WrongAssetType` exception is handled by `resolve_asset_to_class`
        except UnknownAsset:
            if identifier not in CONSTANT_ASSETS:
                raise

            log.debug(f'Attempt to resolve asset {identifier} using the packaged database')
            asset = GlobalDBHandler().resolve_asset_from_packaged_and_store(identifier=identifier)
        # Save it in the cache
        instance.assets_cache.set(identifier, asset)
        return asset

    @staticmethod
    def get_asset_type(identifier: str) -> AssetType:
        # TODO: This is ugly here but is here to avoid a cyclic import in the Assets file
        # Couldn't find a reorg that solves this cyclic import
        from rotkehlchen.constants.assets import CONSTANT_ASSETS  # pylint: disable=import-outside-toplevel  # isort:skip  # noqa: E501
        from rotkehlchen.globaldb.handler import GlobalDBHandler   # pylint: disable=import-outside-toplevel  # isort:skip  # noqa: E501

        instance = AssetResolver()
        cached_data = instance.types_cache.get(identifier)
        if cached_data is not None:
            return cached_data

        try:
            asset_type = GlobalDBHandler().get_asset_type(identifier)
        except UnknownAsset:
            if identifier not in CONSTANT_ASSETS:
                raise

            log.debug(f'Attempt to get asset_type for {identifier} using the packaged database')
            asset = GlobalDBHandler().resolve_asset_from_packaged_and_store(identifier=identifier)
            asset_type = asset.asset_type
        instance.types_cache.set(identifier, asset_type)
        return asset_type

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
        from rotkehlchen.constants.assets import CONSTANT_ASSETS  # pylint: disable=import-outside-toplevel  # isort:skip  # noqa: E501
        from rotkehlchen.globaldb.handler import GlobalDBHandler   # pylint: disable=import-outside-toplevel  # isort:skip  # noqa: E501

        resolved_asset = AssetResolver().resolve_asset(identifier=identifier)
        if isinstance(resolved_asset, expected_type) is True:
            # resolve_asset returns Asset, but we already narrow type with the if check above
            return resolved_asset  # type: ignore

        if identifier in CONSTANT_ASSETS:
            # Check if the version in the packaged globaldb is correct
            resolved_asset = GlobalDBHandler().resolve_asset_from_packaged_and_store(identifier=identifier)  # noqa: E501
            AssetResolver().assets_cache.set(identifier, resolved_asset)
            if isinstance(resolved_asset, expected_type) is True:
                # resolve_asset returns Asset, but we already narrow type with the if check above
                return resolved_asset  # type: ignore

        raise WrongAssetType(
            identifier=identifier,
            expected_type=expected_type,
            real_type=type(resolved_asset),
        )
