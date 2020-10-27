from typing import Union

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.errors import UnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.typing import AssetType, EthTokenInfo


def token_normalized_value_decimals(token_amount: int, token_decimals: int) -> FVal:
    return token_amount / (FVal(10) ** FVal(token_decimals))


def token_normalized_value(token_amount: int, token: Union[EthereumToken, EthTokenInfo]) -> FVal:
    return token_normalized_value_decimals(token_amount, token.decimals)


def asset_normalized_value(amount: int, asset: Asset) -> FVal:
    """Takes in an amount and an asset and returns its normalized value

    May raise:
    - UnsupportedAsset if the given asset is not ETH or an ethereum token
    """
    if asset.identifier == 'ETH':
        decimals = 18
    else:
        if asset.asset_type != AssetType.ETH_TOKEN:
            raise UnsupportedAsset(asset.identifier)
        decimals = asset.decimals  # type: ignore

    return token_normalized_value_decimals(amount, decimals)
