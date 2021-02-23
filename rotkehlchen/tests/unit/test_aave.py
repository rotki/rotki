from rotkehlchen.chain.ethereum.modules.aave.common import (
    AAVE_RESERVE_TO_ASSET,
    ATOKEN_TO_DEPLOYED_BLOCK,
)
from rotkehlchen.constants.ethereum import AAVE_ETH_RESERVE_ADDRESS


def test_aave_reserve_mapping():
    assert len(ATOKEN_TO_DEPLOYED_BLOCK) == len(AAVE_RESERVE_TO_ASSET)
    for address, asset in AAVE_RESERVE_TO_ASSET.items():
        if address == AAVE_ETH_RESERVE_ADDRESS:
            continue

        msg = f'Wrong address for {asset.symbol}. Expected {asset.ethereum_address} got {address}'
        assert address == asset.ethereum_address, msg
