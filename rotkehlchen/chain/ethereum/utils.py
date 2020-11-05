from typing import TYPE_CHECKING, Any, List, Optional, Sequence, Tuple, Union

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.contracts import EthereumContract
from rotkehlchen.constants.ethereum import ETH_MULTICALL
from rotkehlchen.errors import UnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.typing import AssetType, ChecksumEthAddress, EthTokenInfo

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager, NodeName


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


def multicall(
        ethereum: 'EthereumManager',
        calls: List[Tuple[ChecksumEthAddress, str]],
        call_order: Optional[Sequence['NodeName']] = None,
):
    multicall_result = ETH_MULTICALL.call(
        ethereum=ethereum,
        method_name='aggregate',
        arguments=[calls],
        call_order=call_order,
    )
    block, output = multicall_result
    return output


def multicall_specific(
        ethereum: 'EthereumManager',
        contract: EthereumContract,
        method_name: str,
        arguments: List[Any],
        call_order: Optional[Sequence['NodeName']] = None,
):
    calls = [(
        contract.address,
        contract.encode(method_name=method_name, arguments=[i]),
    ) for i in arguments]
    output = multicall(ethereum, calls, call_order)
    return [contract.decode(x, method_name, [arguments[0]]) for x in output]
