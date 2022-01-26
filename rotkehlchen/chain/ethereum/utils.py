import json
from typing import TYPE_CHECKING, Any, List, Optional, Sequence, Tuple

from eth_utils import event_abi_to_log_topic, to_checksum_address
from web3 import Web3
from web3._utils.abi import (
    exclude_indexed_event_inputs,
    get_abi_input_names,
    get_indexed_event_inputs,
    map_abi_data,
    normalize_event_input_types,
)
from web3._utils.events import get_event_abi_types_for_decoding
from web3._utils.normalizers import BASE_RETURN_NORMALIZERS
from web3.types import ABIEvent

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.contracts import EthereumContract
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.constants.ethereum import ETH_MULTICALL, ETH_MULTICALL_2
from rotkehlchen.errors import DeserializationError, UnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.typing import ChecksumEthAddress
from rotkehlchen.utils.misc import hexstring_to_bytes

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager, NodeName

WEB3 = Web3()

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


def token_normalized_value_decimals(token_amount: int, token_decimals: Optional[int]) -> FVal:
    if token_decimals is None:  # if somehow no info on decimals ends up here assume 18
        token_decimals = 18

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

    May raise:
    - DeserializationError
    """
    contract_address = Web3.keccak(
        hexstring_to_bytes('0xff') +
        hexstring_to_bytes(address) +
        hexstring_to_bytes(salt) +
        Web3.keccak(hexstring_to_bytes(init_code)),
    )[12:].hex()
    return to_checksum_address(contract_address)


def decode_event_data(log: EthereumTxReceiptLog, abi_json: str):
    """This is an adjustment of web3's event data decoding to work with our code
    source: https://github.com/ethereum/web3.py/blob/ffe59daf10edc19ee5f05227b25bac8d090e8aa4/web3/_utils/events.py#L201

    May raise:
    - DeserializationError if the abi string is invalid or abi or log topics/data do not match
    """  # noqa: E501
    try:
        event_abi = json.loads(abi_json)
    except json.decoder.JSONDecodeError as e:
        raise DeserializationError('Failed to read the given event abi into json') from e

    if event_abi['anonymous']:
        topics = log.topics
    elif len(log.topics) == 0:
        raise DeserializationError('Expected non-anonymous event to have 1 or more topics')
    # type ignored b/c event_abi_to_log_topic(event_abi: Dict[str, Any])
    elif event_abi_to_log_topic(event_abi) != log.topics[0]:  # type: ignore
        raise DeserializationError('The event signature did not match the provided ABI')
    else:
        topics = log.topics[1:]

    log_topics_abi = get_indexed_event_inputs(event_abi)
    log_topic_normalized_inputs = normalize_event_input_types(log_topics_abi)
    log_topic_types = get_event_abi_types_for_decoding(log_topic_normalized_inputs)
    log_topic_names = get_abi_input_names(ABIEvent({'inputs': log_topics_abi}))

    if len(topics) != len(log_topic_types):
        raise DeserializationError('Expected {0} log topics.  Got {1}'.format(
            len(log_topic_types),
            len(topics),
        ))

    log_data_abi = exclude_indexed_event_inputs(event_abi)
    log_data_normalized_inputs = normalize_event_input_types(log_data_abi)
    log_data_types = get_event_abi_types_for_decoding(log_data_normalized_inputs)
    log_data_names = get_abi_input_names(ABIEvent({'inputs': log_data_abi}))

    # sanity check that there are not name intersections between the topic
    # names and the data argument names.
    duplicate_names = set(log_topic_names).intersection(log_data_names)
    if duplicate_names:
        raise DeserializationError(
            f"The following argument names are duplicated "
            f"between event inputs: '{', '.join(duplicate_names)}'",
        )

    decoded_log_data = WEB3.codec.decode_abi(log_data_types, log.data)
    normalized_log_data = map_abi_data(
        BASE_RETURN_NORMALIZERS,
        log_data_types,
        decoded_log_data,
    )
    decoded_topic_data = [
        WEB3.codec.decode_single(topic_type, topic_data)
        for topic_type, topic_data
        in zip(log_topic_types, topics)
    ]
    normalized_topic_data = map_abi_data(
        BASE_RETURN_NORMALIZERS,
        log_topic_types,
        decoded_topic_data,
    )
    return normalized_topic_data, normalized_log_data
