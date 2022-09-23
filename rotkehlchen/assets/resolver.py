from typing import TYPE_CHECKING, Dict, Optional, Type, TypeVar

from rotkehlchen.assets.types import AssetType
from rotkehlchen.errors.asset import WrongAssetType

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset


T = TypeVar('T')


class AssetResolver():
    __instance: Optional['AssetResolver'] = None
    # A cache so that the DB is not hit every time
    # the cache maps identifier -> deepest representation of the asset
    assets_cache: Dict[str, 'Asset'] = {}
    types_cache: Dict[str, AssetType] = {}

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

        if identifier is None:  # clean all
            AssetResolver.__instance.assets_cache.clear()
        else:
            AssetResolver.__instance.assets_cache.pop(identifier.lower(), None)

    @staticmethod
    def resolve_asset(
            identifier: str,
            form_with_incomplete_data: bool = False,
    ) -> 'Asset':  # returns any subclass
        """Get all asset data for a valid asset identifier

        Raises UnknownAsset if no data can be found
        """
        # This is ugly here but is here to avoid a cyclic import in the Assets file
        # Couldn't find a reorg that solves this cyclic import
        from rotkehlchen.globaldb.handler import \
            GlobalDBHandler  # pylint: disable=import-outside-toplevel  # noqa: E501

        instance = AssetResolver()
        # attempt read from memory cache -- always lower
        cached_data = instance.assets_cache.get(identifier.lower(), None)
        if cached_data is not None:
            return cached_data

        # If was not found in the cache try querying it in the globaldb
        asset = GlobalDBHandler().resolve_asset(identifier, form_with_incomplete_data)
        instance.assets_cache[identifier.lower()] = asset
        return asset

    @staticmethod
    def get_asset_type(identifier: str) -> AssetType:
        # This is ugly here but is here to avoid a cyclic import in the Assets file
        # Couldn't find a reorg that solves this cyclic import
        from rotkehlchen.globaldb.handler import \
            GlobalDBHandler  # pylint: disable=import-outside-toplevel

        instance = AssetResolver()
        cached_data = instance.types_cache.get(identifier)
        if cached_data is not None:
            return cached_data

        type_in_db = GlobalDBHandler().get_asset_type(identifier)
        instance.types_cache[identifier] = type_in_db
        return type_in_db

    @staticmethod
    def resolve_asset_to_class(
            identifier: str,
            expected_type: Type[T],
            form_with_incomplete_data: bool = False,
    ) -> T:
        resolved_asset = AssetResolver().resolve_asset(identifier, form_with_incomplete_data)
        if isinstance(resolved_asset, expected_type) is False:
            raise WrongAssetType(
                identifier=identifier,
                expected_type=expected_type,
                real_type=type(resolved_asset),
            )
        return resolved_asset  # type: ignore
