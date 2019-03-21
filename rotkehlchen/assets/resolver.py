import os
from typing import Any, Dict

from rotkehlchen.typing import AssetData, AssetType
from rotkehlchen.utils import rlk_jsonloads_dict

asset_type_mapping = {
    'fiat': AssetType.FIAT,
    'own chain': AssetType.OWN_CHAIN,
    'ethereum token': AssetType.ETH_TOKEN,
    'omni token': AssetType.OMNI_TOKEN,
    'neo token': AssetType.NEO_TOKEN,
    'counterparty token': AssetType.XCP_TOKEN,
    'bitshares token': AssetType.BTS_TOKEN,
    'ardor token': AssetType.ARDOR_TOKEN,
    'nxt token': AssetType.NXT_TOKEN,
    'Ubiq token': AssetType.UBIQ_TOKEN,
    'Nubits token': AssetType.NUBITS_TOKEN,
    'Burst token': AssetType.BURST_TOKEN,
    'waves token': AssetType.WAVES_TOKEN,
}


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
    def is_symbol_canonical(asset_symbol: str) -> bool:
        """Checks if an asset symbol is canonical"""
        return asset_symbol in AssetResolver().assets

    @staticmethod
    def get_asset_data(asset_symbol: str) -> AssetData:
        """Get all asset data from the known assets file for valid asset symbol"""
        data = AssetResolver().assets[asset_symbol]
        asset_type = asset_type_mapping[data['type']]
        result = AssetData(
            symbol=asset_symbol,
            name=data['name'],
            # If active is in the data use it, else we assume it's true
            active=data.get('active', True),
            asset_type=asset_type,
            started=data.get('started', None),
            ended=data.get('ended', None),
            forked=data.get('forked', None),
            swapped_for=data.get('swapped_for', None),
        )
        return result
