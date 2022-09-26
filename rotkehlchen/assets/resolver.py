from typing import TYPE_CHECKING, Optional, Type, TypeVar

from rotkehlchen.assets.types import AssetType
from rotkehlchen.errors.asset import WrongAssetType
from rotkehlchen.utils.data_structures import LRUCacheWithRemove

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset


T = TypeVar('T')


class AssetResolver():
    __instance: Optional['AssetResolver'] = None
    # A cache so that the DB is not hit every time
    # the cache maps identifier -> deepest representation of the asset
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
    def resolve_asset(
            identifier: str,
            form_with_incomplete_data: bool = False,
    ) -> 'Asset':
        """
        Get all asset data for a valid asset identifier. May return any valid subclass of the
        Asset class.

        Raises UnknownAsset if no data can be found
        """
        # TODO: This is ugly here but is here to avoid a cyclic import in the Assets file
        # Couldn't find a reorg that solves this cyclic import
        from rotkehlchen.globaldb.handler import \
            GlobalDBHandler  # pylint: disable=import-outside-toplevel  # noqa: E501

        instance = AssetResolver()
        cached_data = instance.assets_cache.get(identifier)
        if cached_data is not None:
            return cached_data

        # If was not found in the cache try querying it in the globaldb
        asset = GlobalDBHandler().resolve_asset(identifier, form_with_incomplete_data)
        # Save it in the cache
        instance.assets_cache.set(identifier, asset)
        return asset

    @staticmethod
    def get_asset_type(identifier: str) -> AssetType:
        # TODO: This is ugly here but is here to avoid a cyclic import in the Assets file
        # Couldn't find a reorg that solves this cyclic import
        from rotkehlchen.globaldb.handler import \
            GlobalDBHandler  # pylint: disable=import-outside-toplevel

        instance = AssetResolver()
        cached_data = instance.types_cache.get(identifier)
        if cached_data is not None:
            return cached_data

        asset_type = GlobalDBHandler().get_asset_type(identifier)
        instance.types_cache.set(identifier, asset_type)
        return asset_type

    @staticmethod
    def resolve_asset_to_class(
            identifier: str,
            expected_type: Type[T],
            form_with_incomplete_data: bool = False,
    ) -> T:
        """
        Try to resolve an identifier to the Asset subclass defined in expected_type.
        May raise:
        - WrongAssetType: if the asset is resolved but the class is not the expected one.
        - UnknownAsset: if the asset was not found in the database.
        """
        resolved_asset = AssetResolver().resolve_asset(identifier, form_with_incomplete_data)
        if isinstance(resolved_asset, expected_type) is False:
            raise WrongAssetType(
                identifier=identifier,
                expected_type=expected_type,  # type: ignore # it expect it to be T but since is dinamic doesn't recognize it as the Asset type  # noqa: E501
                real_type=type(resolved_asset),  # type: ignore  # same as above
            )
        # We ignore the type here because the linter fails to detect that is properly checked
        # above section since is checked in runtype and `resolve_asset` can return any type.
        return resolved_asset  # type: ignore
