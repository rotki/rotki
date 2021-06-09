from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple

from eth_utils import to_bytes, to_checksum_address
from web3 import Web3
from web3._utils.abi import exclude_indexed_event_inputs, normalize_event_input_types
from web3._utils.encoding import hexstr_if_str
from web3._utils.events import get_event_abi_types_for_decoding

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.contracts import EthereumContract
from rotkehlchen.constants.ethereum import ETH_MULTICALL, ETH_MULTICALL_2
from rotkehlchen.errors import UnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.typing import ChecksumEthAddress
from rotkehlchen.utils.misc import hexstring_to_bytes

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager, NodeName

ABI_CODEC = Web3().codec
# TODO: remove this once web3.py updates ENS library for supporting multichain
# https://github.com/ethereum/web3.py/issues/1839
ENS_RESOLVER_ABI_MULTICHAIN_ADDRESS = [
    {
        "constant": True,
        "inputs": [
            {
                "name": "node",
                "type": "bytes32",
            },
            {
                "name": "coinType",
                "type": "uint256",
            },
        ],
        "name": "addr",
        "outputs": [
            {
                "name": "ret",
                "type": "bytes",
            },
        ],
        "payable": False,
        "type": "function",
    },
]


def token_normalized_value_decimals(token_amount: int, token_decimals: int) -> FVal:
    return token_amount / (FVal(10) ** FVal(token_decimals))


def token_normalized_value(
        token_amount: int,
        token: EthereumToken,
) -> FVal:
    return token_normalized_value_decimals(token_amount, token.decimals)


def asset_normalized_value(amount: int, asset: Asset) -> FVal:
    """Takes in an amount and an asset and returns its normalized value

    May raise:
    - UnsupportedAsset if the given asset is not ETH or an ethereum token
    """
    if asset.identifier == 'ETH':
        decimals = 18
    else:
        token = EthereumToken.from_asset(asset)
        if token is None:
            raise UnsupportedAsset(asset.identifier)
        decimals = token.decimals

    return token_normalized_value_decimals(amount, decimals)


def multicall(
        ethereum: 'EthereumManager',
        calls: List[Tuple[ChecksumEthAddress, str]],
        call_order: Optional[Sequence['NodeName']] = None,
) -> Any:
    multicall_result = ETH_MULTICALL.call(
        ethereum=ethereum,
        method_name='aggregate',
        arguments=[calls],
        call_order=call_order,
    )
    _, output = multicall_result
    return output


def multicall_2(
        ethereum: 'EthereumManager',
        calls: List[Tuple[ChecksumEthAddress, str]],
        require_success: bool,
        call_order: Optional[Sequence['NodeName']] = None,
) -> List[Tuple[bool, bytes]]:
    """
    Use a MULTICALL_2 contract for an aggregated query. If require_success
    is set to False any call in the list of calls is allowed to fail.
    """
    return ETH_MULTICALL_2.call(
        ethereum=ethereum,
        method_name='tryAggregate',
        arguments=[require_success, calls],
        call_order=call_order,
    )


def multicall_specific(
        ethereum: 'EthereumManager',
        contract: EthereumContract,
        method_name: str,
        arguments: List[Any],
        call_order: Optional[Sequence['NodeName']] = None,
) -> Any:
    calls = [(
        contract.address,
        contract.encode(method_name=method_name, arguments=i),
    ) for i in arguments]
    output = multicall(ethereum, calls, call_order)
    return [contract.decode(x, method_name, arguments[0]) for x in output]


def decode_event_data(data: str, event_abi: Dict[str, Any]) -> Tuple:
    """Decode the data of an event according to the event's abi entry"""
    log_data = hexstr_if_str(to_bytes, data)
    log_data_abi = exclude_indexed_event_inputs(event_abi)  # type: ignore
    log_data_normalized_inputs = normalize_event_input_types(log_data_abi)
    log_data_types = get_event_abi_types_for_decoding(log_data_normalized_inputs)
    decoded_log_data = ABI_CODEC.decode_abi(log_data_types, log_data)
    return decoded_log_data


def generate_address_via_create2(
        address: str,
        salt: str,
        init_code: str,
) -> ChecksumEthAddress:
    """Python implementation of CREATE2 opcode.

    Given an address (deployer), a salt and an init code (contract creation
    bytecode), returns the expected contract address once it is deployed.

    Pseudocode:
        keccak256( 0xff ++ address ++ salt ++ keccak256(init_code))[12:]

    EIP-1014:
    https://github.com/ethereum/EIPs/blob/master/EIPS/eip-1014.md
    """
    contract_address = Web3.keccak(
        hexstring_to_bytes('0xff') +
        hexstring_to_bytes(address) +
        hexstring_to_bytes(salt) +
        Web3.keccak(hexstring_to_bytes(init_code)),
    )[12:].hex()
    return to_checksum_address(contract_address)
