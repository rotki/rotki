import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, List, NamedTuple, Set, Tuple

import requests

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.utils import get_or_create_ethereum_token
from rotkehlchen.chain.ethereum.contracts import EthereumContract
from rotkehlchen.chain.ethereum.defi.zerionsdk import ZERION_ADAPTER_ADDRESS
from rotkehlchen.chain.ethereum.typing import NodeName
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.constants.ethereum import ZERION_ABI
from rotkehlchen.fval import FVal
from rotkehlchen.typing import ChecksumEthAddress
from rotkehlchen.utils.misc import get_chunks

from .typing import LiquidityPool, LiquidityPoolAsset

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler


log = logging.getLogger(__name__)


SUBGRAPH_REMOTE_ERROR_MSG = (
    "Failed to request the Uniswap subgraph due to {error_msg}. "
    "All Uniswap balances and historical queries are not functioning until this is fixed. "  # noqa: E501
    "Probably will get fixed with time. If not report it to rotki's support channel"  # noqa: E501
)


class TokenDetails(NamedTuple):
    address: ChecksumEthAddress
    name: str
    symbol: str
    decimals: int
    amount: FVal


def _decode_token(entry: Tuple) -> TokenDetails:
    decimals = entry[0][3]
    return TokenDetails(
        address=entry[0][0],
        name=entry[0][1],
        symbol=entry[0][2],
        decimals=decimals,
        amount=token_normalized_value_decimals(entry[1], decimals),
    )


def _decode_result(
        userdb: 'DBHandler',
        data: Tuple,
        known_assets: Set[EthereumToken],
        unknown_assets: Set[EthereumToken],
) -> LiquidityPool:
    pool_token = _decode_token(data[0])
    token0 = _decode_token(data[1][0])
    token1 = _decode_token(data[1][1])

    assets = []
    for token in (token0, token1):
        asset = get_or_create_ethereum_token(
            userdb=userdb,
            symbol=token.symbol,
            ethereum_address=token.address,
            name=token.name,
            decimals=token.decimals,
        )
        # Classify the asset either as price known or unknown
        if asset.has_oracle():
            known_assets.add(asset)
        else:
            unknown_assets.add(asset)
        assets.append(LiquidityPoolAsset(
            asset=asset,
            total_amount=None,
            user_balance=Balance(amount=token.amount),
        ))

    pool = LiquidityPool(
        address=pool_token.address,
        assets=assets,
        total_supply=None,
        user_balance=Balance(amount=pool_token.amount),
    )
    return pool


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
        response = requests.get('https://raw.githubusercontent.com/rotki/rotki/develop/rotkehlchen/data/uniswapv2_lp_tokens.meta')  # noqa: E501
        remote_meta = response.json()
        if our_downloaded_meta.is_file():
            local_meta_file = our_downloaded_meta
        else:
            local_meta_file = our_builtin_meta

        with open(local_meta_file, 'r') as f:
            local_meta = json.loads(f.read())

        if local_meta['version'] < remote_meta['version']:
            # we need to download and save the new assets from github
            response = requests.get('https://raw.githubusercontent.com/rotki/rotki/develop/rotkehlchen/data/uniswapv2_lp_tokens.json')  # noqa: E501
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
