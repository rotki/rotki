import os
from dataclasses import dataclass
from typing import Any, Dict

from rotkehlchen.errors import UnknownAsset
from rotkehlchen.utils import rlk_jsonloads_dict


class AssetKeeper():
    __instance = None
    assets: Dict[str, Dict[str, Any]] = None

    def __new__(cls):
        if AssetKeeper.__instance is not None:
            return AssetKeeper.__instance

        AssetKeeper.__instance = object.__new__(cls)

        dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        with open(os.path.join(dir_path, 'data', 'all_assets.json'), 'r') as f:
            assets = set(rlk_jsonloads_dict(f.read()))

        AssetKeeper.__instance.gateway = assets
        return AssetKeeper.__instance

    @staticmethod
    def is_name_canonical(asset_name: str) -> bool:
        return asset_name in AssetKeeper().assets


@dataclass(init=False, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class Asset():
    name: str

    def __init__(self, asset_name: str):
        if not AssetKeeper().is_name_canonical(asset_name):
            raise UnknownAsset(asset_name)

    def canonical(self) -> str:
        return self.name
