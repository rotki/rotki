import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Set

import requests
from web3.types import BlockIdentifier

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.contracts import EthereumContract
from rotkehlchen.chain.ethereum.defi.zerionsdk import ZERION_ADAPTER_ADDRESS
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import LiquidityPool
from rotkehlchen.chain.ethereum.interfaces.ammswap.utils import _decode_result
from rotkehlchen.chain.ethereum.types import WeightedNode
from rotkehlchen.chain.ethereum.utils import multicall, multicall_2
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.ethereum import UNISWAP_V2_LP_ABI, ZERION_ABI
from rotkehlchen.constants.misc import ONE
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEthAddress, Price, Timestamp
from rotkehlchen.utils.misc import get_chunks

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


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
    if (own_node_info := ethereum.get_own_node_info()) is not None:
        chunks = list(get_chunks(lp_addresses, n=4000))
        call_order = [WeightedNode(node_info=own_node_info, weight=ONE)]
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
