from typing import Dict, Optional

from rotkehlchen.errors import UnknownAsset
from rotkehlchen.globaldb import GlobalDBHandler

from .typing import AssetData


class AssetResolver():
    __instance: Optional['AssetResolver'] = None
    # A cache so that the DB is not hit every time
    assets_cache: Dict[str, AssetData] = {}

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
    def get_asset_data(
            asset_identifier: str,
            form_with_incomplete_data: bool = False,
    ) -> AssetData:
        """Get all asset data for a valid asset identifier

        Raises UnknownAsset if no data can be found
        """
        instance = AssetResolver()
        # attempt read from memory cache -- always lower
        cached_data = instance.assets_cache.get(asset_identifier.lower(), None)
        if cached_data is not None:
            return cached_data

        dbinstance = GlobalDBHandler()
        # At this point we can use the global DB
        asset_data = dbinstance.get_asset_data(asset_identifier, form_with_incomplete_data)
        if asset_data is None:
            raise UnknownAsset(asset_identifier)

        # save in the memory cache -- always lower
        instance.assets_cache[asset_identifier.lower()] = asset_data
        return asset_data
