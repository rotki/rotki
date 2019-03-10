import os
from typing import Any, Dict

from rotkehlchen.utils import rlk_jsonloads_dict


class AssetResolver():
    __instance = None
    assets: Dict[str, Dict[str, Any]] = None

    def __new__(cls):
        if AssetResolver.__instance is not None:
            return AssetResolver.__instance

        AssetResolver.__instance = object.__new__(cls)

        dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        with open(os.path.join(dir_path, 'data', 'all_assets.json'), 'r') as f:
            assets = rlk_jsonloads_dict(f.read())

        AssetResolver.__instance.assets = assets
        return AssetResolver.__instance

    @staticmethod
    def is_name_canonical(asset_name: str) -> bool:
        return asset_name in AssetResolver().assets
