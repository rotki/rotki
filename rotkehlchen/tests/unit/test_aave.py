from rotkehlchen.chain.ethereum.modules.aave.common import (
    aave_reserve_to_asset,
    asset_to_aave_reserve,
)
from rotkehlchen.chain.ethereum.modules.aave.constants import (
    ATOKEN_TO_DEPLOYED_BLOCK,
    ATOKENS_LIST,
    ATOKENV1_TO_ASSET,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.ethereum import AAVE_ETH_RESERVE_ADDRESS


def test_aave_reserve_mapping():
    assert len(ATOKEN_TO_DEPLOYED_BLOCK) == len(ATOKENV1_TO_ASSET)
    for token in ATOKENS_LIST:
        underlying_asset = ATOKENV1_TO_ASSET[token]
        if underlying_asset == A_ETH:
            assert asset_to_aave_reserve(underlying_asset) == AAVE_ETH_RESERVE_ADDRESS
            continue

        assert aave_reserve_to_asset(underlying_asset.ethereum_address) == underlying_asset
        assert asset_to_aave_reserve(underlying_asset) == underlying_asset.ethereum_address
