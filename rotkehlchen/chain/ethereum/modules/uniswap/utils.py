import itertools
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Set, Tuple

import requests
from eth_abi import encode_abi
from eth_abi.packed import encode_abi_packed
from eth_typing import ChecksumAddress
from eth_utils import to_checksum_address
from web3 import Web3
from web3.types import BlockIdentifier

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.contracts import EthereumContract
from rotkehlchen.chain.ethereum.defi.zerionsdk import ZERION_ADAPTER_ADDRESS
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import LiquidityPool, NFTLiquidityPool
from rotkehlchen.chain.ethereum.interfaces.ammswap.utils import _decode_result, _decode_v3_result
from rotkehlchen.chain.ethereum.types import NodeName, string_to_ethereum_address
from rotkehlchen.chain.ethereum.utils import multicall, multicall_2
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.ethereum import (
    UNISWAP_V2_LP_ABI,
    UNISWAP_V3_NFT_MANAGER_ABI,
    UNISWAP_V3_POOL_ABI,
    ZERION_ABI,
)
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import ChecksumEthAddress, Price, Timestamp
from rotkehlchen.utils.misc import get_chunks

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

UNISWAP_NFT_MANAGER_ADDRESS = string_to_ethereum_address(to_checksum_address('0xc36442b4a4522e871399cd717abdd847ab11fe88'))  # noqa: 501
POOL_INIT_CODE_HASH = '0xe34f199b19b2b4f47f68442619d555527d244f78a3297ea89325f843f87b8b54'
UNISWAP_V3_FACTORY_ADDRESS = string_to_ethereum_address('0x1F98431c8aD98523631AE4a59f267346ea31F984')  # noqa: 501
UNISWAP_V3_DEPLOYED_BLOCK = 12369651


def uniswap_lp_token_balances(
        userdb: 'DBHandler',
        address: ChecksumEthAddress,
        ethereum: 'EthereumManager',
        lp_addresses: List[ChecksumEthAddress],
        known_assets: Set[EthereumToken],
        unknown_assets: Set[EthereumToken],
) -> List[LiquidityPool]:
    """Query uniswap token balances from ethereum chain

    The number of addresses to query in one call depends a lot on the node used.
    With an infura node we saw the following:
    500 addresses per call took on average 43 seconds for 20450 addresses
    2000 addresses per call took on average 36 seconds for 20450 addresses
    4000 addresses per call took on average 32.6 seconds for 20450 addresses
    5000 addresses timed out a few times
    """
    zerion_contract = EthereumContract(
        address=ZERION_ADAPTER_ADDRESS,
        abi=ZERION_ABI,
        deployed_block=1586199170,
    )
    if NodeName.OWN in ethereum.web3_mapping:
        chunks = list(get_chunks(lp_addresses, n=4000))
        call_order = [NodeName.OWN]
    else:
        chunks = list(get_chunks(lp_addresses, n=700))
        call_order = ethereum.default_call_order(skip_etherscan=True)

    balances = []
    for chunk in chunks:
        result = zerion_contract.call(
            ethereum=ethereum,
            method_name='getAdapterBalance',
            arguments=[address, '0x4EdBac5c8cb92878DD3fd165e43bBb8472f34c3f', chunk],
            call_order=call_order,
        )

        for entry in result[1]:
            balances.append(_decode_result(userdb, entry, known_assets, unknown_assets))

    return balances


def get_latest_lp_addresses(data_directory: Path) -> List[ChecksumEthAddress]:
    """Gets the latest lp addresses either locally or from the remote

    Checks the remote (github) and if there is a newer file there it pulls it,
    saves it and its md5 hash locally and returns the new lp addresses.

    If there is no new file (same hash) or if there is any problem contacting the remote
    then the builtin lp assets file is used.

    TODO: This is very similar to assets/resolver.py::_get_latest_assets
    Perhaps try to abstract it away?
    """
    root_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    our_downloaded_meta = data_directory / 'assets' / 'uniswapv2_lp_tokens.meta'
    our_builtin_meta = root_dir / 'data' / 'uniswapv2_lp_tokens.meta'
    try:
        response = requests.get(
            url='https://raw.githubusercontent.com/rotki/rotki/develop/rotkehlchen/data/uniswapv2_lp_tokens.meta',  # noqa: E501,
            timeout=DEFAULT_TIMEOUT_TUPLE,
        )
        remote_meta = response.json()
        if our_downloaded_meta.is_file():
            local_meta_file = our_downloaded_meta
        else:
            local_meta_file = our_builtin_meta

        with open(local_meta_file, 'r') as f:
            local_meta = json.loads(f.read())

        if local_meta['version'] < remote_meta['version']:
            # we need to download and save the new assets from github
            response = requests.get(
                url='https://raw.githubusercontent.com/rotki/rotki/develop/rotkehlchen/data/uniswapv2_lp_tokens.json',  # noqa: E501
                timeout=DEFAULT_TIMEOUT_TUPLE,
            )
            remote_data = response.text

            # Make sure directory exists
            (data_directory / 'assets').mkdir(parents=True, exist_ok=True)
            # Write the files
            with open(data_directory / 'assets' / 'uniswapv2_lp_tokens.meta', 'w') as f:
                f.write(json.dumps(remote_meta))
            with open(data_directory / 'assets' / 'uniswapv2_lp_tokens.json', 'w') as f:
                f.write(remote_data)

            log.info(
                f'Found newer remote uniswap lp tokens file with version: {remote_meta["version"]}'
                f' and {remote_meta["md5"]} md5 hash. Replaced local file',
            )
            return json.loads(remote_data)

        # else, same as all error cases use the current one
    except (requests.exceptions.RequestException, KeyError, json.decoder.JSONDecodeError):
        pass

    if our_downloaded_meta.is_file():
        assets_file = data_directory / 'assets' / 'uniswapv2_lp_tokens.json'
    else:
        assets_file = root_dir / 'data' / 'uniswapv2_lp_tokens.json'

    with open(assets_file, 'r') as f:
        return json.loads(f.read())


def find_uniswap_v2_lp_price(
        ethereum: 'EthereumManager',
        token: EthereumToken,
        token_price_func: Callable,
        token_price_func_args: List[Any],
        block_identifier: BlockIdentifier,
) -> Optional[Price]:
    """
    Calculate the price for a uniswap v2 LP token. That is
    value = (Total value of liquidity pool) / (Current suply of LP tokens)
    We need:
    - Price of token 0
    - Price of token 1
    - Pooled amount of token 0
    - Pooled amount of token 1
    - Total supply of of pool token
    """
    address = token.ethereum_address
    contract = EthereumContract(address=address, abi=UNISWAP_V2_LP_ABI, deployed_block=0)
    methods = ['token0', 'token1', 'totalSupply', 'getReserves', 'decimals']
    multicall_method = multicall_2  # choose which multicall to use
    if isinstance(block_identifier, int):
        if block_identifier <= 7929876:
            log.error(
                f'No multicall contract at the block {block_identifier}. Uniswap v2 LP '
                f'query failed. Should implement direct queries',
            )
            return None

        if block_identifier <= 12336033:
            multicall_method = multicall

    try:
        output = multicall_method(
            ethereum=ethereum,
            require_success=True,
            calls=[(address, contract.encode(method_name=method)) for method in methods],
            block_identifier=block_identifier,
        )
    except RemoteError as e:
        log.error(
            f'Remote error calling multicall contract for uniswap v2 lp '
            f'token {token.ethereum_address} properties: {str(e)}',
        )
        return None

    # decode output
    decoded = []
    for (method_output, method_name) in zip(output, methods):
        call_success = True
        if multicall_method == multicall_2:
            call_success = method_output[0]
            call_result = method_output[1]
        else:
            call_result = method_output  # type: ignore
        if call_success and len(call_result) != 0:
            decoded_method = contract.decode(call_result, method_name)
            if len(decoded_method) == 1:
                # https://github.com/PyCQA/pylint/issues/4739
                decoded.append(decoded_method[0])  # pylint: disable=unsubscriptable-object
            else:
                decoded.append(decoded_method)
        else:
            log.debug(
                f'Multicall to Uniswap V2 LP failed to fetch field {method_name} '
                f'for token {token.ethereum_address}',
            )
            return None

    try:
        token0 = EthereumToken(decoded[0])
        token1 = EthereumToken(decoded[1])
    except UnknownAsset:
        return None

    try:
        token0_supply = FVal(decoded[3][0] * 10**-token0.decimals)
        token1_supply = FVal(decoded[3][1] * 10**-token1.decimals)
        total_supply = FVal(decoded[2] * 10 ** - decoded[4])
    except ValueError as e:
        log.debug(
            f'Failed to deserialize token amounts for token {address} '
            f'with values {str(decoded)}. f{str(e)}',
        )
        return None
    token0_price = token_price_func(token0, *token_price_func_args)
    token1_price = token_price_func(token1, *token_price_func_args)

    if ZERO in (token0_price, token1_price):
        log.debug(
            f'Couldnt retrieve non zero price information for tokens {token0}, {token1} '
            f'with result {token0_price}, {token1_price}',
        )
    numerator = (token0_supply * token0_price + token1_supply * token1_price)
    share_value = numerator / total_supply
    return Price(share_value)


def historical_uniswap_v2_lp_price(
        ethereum: 'EthereumManager',
        token: EthereumToken,
        to_asset: Asset,
        timestamp: Timestamp,
) -> Optional[Price]:
    block_identifier = ethereum.get_blocknumber_by_time(timestamp)
    return find_uniswap_v2_lp_price(
        ethereum=ethereum,
        token=token,
        token_price_func=PriceHistorian.query_historical_price,
        token_price_func_args=[to_asset, timestamp],
        block_identifier=block_identifier,
    )


def uniswap_v3_lp_token_balances(
    userdb: 'DBHandler',
    address: ChecksumEthAddress,
    ethereum: 'EthereumManager',
    premium: Optional[Premium],
    known_assets: Set[EthereumToken],
    unknown_assets: Set[EthereumToken],
) -> List[NFTLiquidityPool]:
    nft_manager_contract = EthereumContract(
        address=UNISWAP_NFT_MANAGER_ADDRESS,
        abi=UNISWAP_V3_NFT_MANAGER_ABI,
        deployed_block=UNISWAP_V3_DEPLOYED_BLOCK,
    )
    address = to_checksum_address(address)
    my_positions = nft_manager_contract.call(
        ethereum=ethereum,
        method_name="balanceOf",
        arguments=[address],
    )
    balances: List[NFTLiquidityPool] = []
    if my_positions <= 0:
        return balances

    chunks = list(get_chunks(list(range(my_positions)), n=10))
    for chunk in chunks:
        tokens_ids_multicall = multicall_2(
            ethereum=ethereum,
            require_success=True,
            calls=[
                (
                    UNISWAP_NFT_MANAGER_ADDRESS,
                    nft_manager_contract.encode('tokenOfOwnerByIndex', [address, index]),
                )
                for index in chunk
            ],
        )
        tokens_ids = [
            nft_manager_contract.decode(   # pylint: disable=unsubscriptable-object
                result=data[1],
                method_name='tokenOfOwnerByIndex',
                arguments=[address, index],
            )[0]
            for index, data in enumerate(tokens_ids_multicall)
        ]
        positions_multicall = multicall_2(
            ethereum=ethereum,
            require_success=True,
            calls=[
                (
                    UNISWAP_NFT_MANAGER_ADDRESS,
                    nft_manager_contract.encode('positions', [token_id]),
                )
                for token_id in tokens_ids
            ],
        )
        positions = [
            nft_manager_contract.decode(
                result=data[1],
                method_name='positions',
                arguments=[tokens_ids[index]],
            )
            for index, data in enumerate(positions_multicall)
        ]
        pool_addresses = [
            compute_pool_address(
                factory_address=UNISWAP_V3_FACTORY_ADDRESS,
                token0_address=position[2],
                token1_address=position[3],
                fee=position[4],
            )
            for position in positions
        ]
        pool_contracts = [
            EthereumContract(
                address=pool_address,
                abi=UNISWAP_V3_POOL_ABI,
                deployed_block=UNISWAP_V3_DEPLOYED_BLOCK,
            )
            for pool_address in pool_addresses
        ]
        slots_0_multicall = multicall_2(
            ethereum=ethereum,
            require_success=True,
            calls=[
                (entry[0], entry[1].encode('slot0'))
                for entry in zip(pool_addresses, pool_contracts)
            ],
        )
        slots_0 = [
            entry[0].decode(entry[1][1], 'slot0')
            for entry in zip(pool_contracts, slots_0_multicall)
        ]
        tokens_a = [
            ethereum.get_basic_contract_info(to_checksum_address(position[2]))
            for position in positions
        ]
        tokens_b = [
            ethereum.get_basic_contract_info(to_checksum_address(position[3]))
            for position in positions
        ]
        price_ranges = [
            calculate_price_range(
                tick_lower=entry[2][5],
                tick_upper=entry[2][6],
                decimal_0=entry[0]['decimals'],
                decimal_1=entry[1]['decimals'],
            )
            for entry in zip(tokens_a, tokens_b, positions)
        ]
        amounts_0 = [
            calculate_amount_0(
                tick=entry[0][1],
                tick_bottom=entry[1][5],
                tick_top=entry[1][6],
                liquidity=entry[1][7],
                decimals=entry[2]['decimals'],
            )
            for entry in zip(slots_0, positions, tokens_a)
        ]
        amounts_1 = [
            calculate_amount_1(
                tick=entry[0][1],
                tick_bottom=entry[1][5],
                tick_top=entry[1][6],
                liquidity=entry[1][7],
                decimals=entry[2]['decimals'],
            )
            for entry in zip(slots_0, positions, tokens_b)
        ]
        total_tokens_in_pools = []
        if premium:
            liquidity_in_pools_multicall = multicall_2(
                ethereum=ethereum,
                require_success=True,
                calls=[
                    (entry[0], entry[1].encode('liquidity'))
                    for entry in zip(pool_addresses, pool_contracts)
                ],
            )
            liquidity_in_pools = [
                (entry[0].decode(entry[1][1], 'liquidity')[0])
                for entry in zip(pool_contracts, liquidity_in_pools_multicall)
            ]
            for entry in zip(slots_0, liquidity_in_pools, positions, tokens_a, tokens_b):
                total_tokens_in_pools.append(
                    calculate_total_amounts_of_tokens(
                        liquidity=entry[1],
                        tick=entry[0][1],
                        fee=entry[2][4],
                        decimal_0=entry[3]['decimals'],
                        decimal_1=entry[4]['decimals'],
                    ),
                )
        for entry in itertools.zip_longest(
            tokens_ids,
            pool_addresses,
            positions,
            price_ranges,
            tokens_a,
            tokens_b,
            amounts_0,
            amounts_1,
            total_tokens_in_pools,
            fillvalue=(None, None),
        ):
            if entry[6] > ZERO or entry[7] > ZERO:  # type: ignore
                entry[4].update({'amount': entry[6], 'address': entry[2][2], 'total_amount': entry[8][0]})  # type: ignore  # noqa: 501
                entry[5].update({'amount': entry[7], 'address': entry[2][3], 'total_amount': entry[8][1]})  # type: ignore  # noqa: 501
                balances.append(_decode_v3_result(userdb, entry, known_assets, unknown_assets))
    return balances


def compute_pool_address(
    factory_address: ChecksumEthAddress,
    token0_address: ChecksumEthAddress,
    token1_address: ChecksumEthAddress,
    fee: int,
) -> ChecksumAddress:
    """
    Generate the pool address from the Uniswap Factory Address, pair of tokens
    and the fee using CREATE2 opcode.
    """
    token_0 = to_checksum_address(token0_address)
    token_1 = to_checksum_address(token1_address)
    factory_address = to_checksum_address(factory_address)
    parameters = []
    # Sort the addresses
    if int(token_0, 16) < int(token_1, 16):
        parameters = [token_0, token_1, fee]
    else:
        parameters = [token_1, token_0, fee]
    abi_encoded_1 = encode_abi(
        ['address', 'address', 'uint24'],
        parameters,
    )
    # pylint: disable=no-value-for-parameter
    salt = Web3.solidityKeccak(abi_types=['bytes'], values=['0x' + abi_encoded_1.hex()])
    abi_encoded_2 = encode_abi_packed(['address', 'bytes32'], (factory_address, salt))
    # pylint: disable=no-value-for-parameter
    address = Web3.solidityKeccak(abi_types=['bytes', 'bytes'],values=['0xff' + abi_encoded_2.hex(), POOL_INIT_CODE_HASH])[12:]  # noqa: 501
    checksum_address = to_checksum_address(address.hex())
    return checksum_address


def calculate_price_range(
    tick_lower: int,
    tick_upper: int,
    decimal_0: int,
    decimal_1: int,

) -> Tuple[FVal, FVal]:
    """Calculates the price range for a Uniswap V3 LP position."""
    sqrt_a = 1.0001**tick_lower
    sqrt_b = 1.0001**tick_upper

    sqrt_adjusted_a = sqrt_a * 10**(decimal_0 - decimal_1)
    sqrt_adjusted_b = sqrt_b * 10**(decimal_0 - decimal_1)

    return FVal(1 / sqrt_adjusted_b), FVal(1 / sqrt_adjusted_a)


def compute_sqrt_values_for_amounts(
    tick_bottom: int,
    tick_top: int,
    tick: int,
) -> Tuple[float, float, float]:
    """Computes the values for `sqrt`, `sqrt_a`, sqrt_b`"""
    sqrt_a = 1.0001**(tick_bottom / 2) * (2**96)
    sqrt_b = 1.0001**(tick_top / 2) * (2**96)
    sqrt = 1.0001**(tick / 2) * (2**96)
    sqrt = max(min(sqrt, sqrt_b), sqrt_a)

    return sqrt, sqrt_a, sqrt_b


def calculate_amount_0(
    tick_bottom: int,
    liquidity: int,
    tick_top: int,
    decimals: int,
    tick: int,
) -> FVal:
    """Calculates the amount of the first token in the Uniswap V3 LP position."""
    sqrt, _, sqrt_b = compute_sqrt_values_for_amounts(
        tick_bottom=tick_bottom,
        tick_top=tick_top,
        tick=tick,
    )
    amount_0 = (liquidity * 2**96 * (sqrt_b - sqrt) / (sqrt_b * sqrt)) / 10**decimals
    return FVal(amount_0)


def calculate_amount_1(
    tick_bottom: int,
    liquidity: int,
    tick_top: int,
    decimals: int,
    tick: int,
) -> FVal:
    """Calculates the amount of the second token in the Uniswap V3 LP position."""
    sqrt, sqrt_a, _ = compute_sqrt_values_for_amounts(
        tick_bottom=tick_bottom,
        tick_top=tick_top,
        tick=tick,
    )
    amount_1 = liquidity * (sqrt - sqrt_a) / 2**96 / 10**decimals
    return FVal(amount_1)


def calculate_total_amounts_of_tokens(
    liquidity: int,
    tick: int,
    fee: int,
    decimal_0: int,
    decimal_1: int,
) -> Tuple[FVal, FVal]:
    """
    Calculates the total amount of tokens present in a liquidity pool.
    A fee of 10000 represents 200 ticks spacing, 3000 represents 60 ticks spacing and
    500 represents 10 ticks spacing.
    """
    if fee == 10000:
        tick_a = tick - (tick % 200)
        tick_b = tick + 200
    elif fee == 3000:
        tick_a = tick - (tick % 60)
        tick_b = tick + 60
    elif fee == 500:
        tick_a = tick - (tick % 10)
        tick_b = tick + 10

    sqrt_a = 1.0001**(tick_a / 2) * 2**96
    sqrt_b = 1.0001**(tick_b / 2) * 2**96
    total_amount_0 = ((liquidity * 2**96 * (sqrt_b - sqrt_a) / sqrt_b / sqrt_a) / 10**decimal_0)
    total_amount_1 = liquidity * (sqrt_b - sqrt_a) / 2**96 / 10**decimal_1

    return FVal(total_amount_0), FVal(total_amount_1)
