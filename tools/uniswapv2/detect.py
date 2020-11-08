import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional

from eth_utils.address import to_checksum_address

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.chain.ethereum.contracts import EthereumContract
from rotkehlchen.chain.ethereum.graph import Graph
from rotkehlchen.chain.ethereum.manager import (
    ETHEREUM_NODES_TO_CONNECT_AT_START,
    EthereumManager,
    NodeName,
)
from rotkehlchen.chain.ethereum.utils import multicall_specific, token_normalized_value_decimals
from rotkehlchen.chain.ethereum.zerion import DefiBalance, Zerion
from rotkehlchen.constants.ethereum import ZERION_ABI
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.greenlets import GreenletManager
from rotkehlchen.tests.utils.ethereum import wait_until_all_nodes_connected
from rotkehlchen.typing import ChecksumEthAddress
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import get_chunks, ts_now

root_path = Path(__file__).resolve().parent.parent.parent


def init_ethereum(rpc_endpoint: str, use_other_nodes: bool) -> EthereumManager:
    nodes_to_connect = ETHEREUM_NODES_TO_CONNECT_AT_START if use_other_nodes else (NodeName.OWN,)
    msg_aggregator = MessagesAggregator()
    etherscan = Etherscan(database=None, msg_aggregator=msg_aggregator)
    api_key = os.environ.get('ETHERSCAN_API_KEY', None)
    greenlet_manager = GreenletManager(msg_aggregator=msg_aggregator)
    etherscan.api_key = api_key
    ethereum = EthereumManager(
        ethrpc_endpoint=rpc_endpoint,
        etherscan=etherscan,
        database=None,
        msg_aggregator=msg_aggregator,
        greenlet_manager=greenlet_manager,
        connect_at_start=nodes_to_connect,
    )
    wait_until_all_nodes_connected(
        ethereum_manager_connect_at_start=nodes_to_connect,
        ethereum=ethereum,
    )
    zerion = Zerion(ethereum_manager=ethereum, msg_aggregator=msg_aggregator)
    return ethereum, zerion


def pairs_from_ethereum(ethereum: EthereumManager) -> Dict[str, Any]:
    """Detect the uniswap v2 pool tokens by using an ethereum node"""
    contracts_file = Path(__file__).resolve().parent / 'contracts.json'
    with contracts_file.open('r') as f:
        contracts = json.loads(f.read())

    univ2factory = EthereumContract(
        address=contracts['UNISWAPV2FACTORY']['address'],
        abi=contracts['UNISWAPV2FACTORY']['abi'],
        deployed_block=0,  # whatever
    )
    pairs_num = univ2factory.call(ethereum, 'allPairsLength')
    chunks = list(get_chunks([[x] for x in range(pairs_num)], n=500))
    pairs = []
    for idx, chunk in enumerate(chunks):
        print(f'Querying univ2 pairs chunk {idx + 1} / {len(chunks)}')
        result = multicall_specific(ethereum, univ2factory, 'allPairs', chunk)
        pairs.extend([to_checksum_address(x[0]) for x in result])

    return pairs


class UniLPBalance(NamedTuple):
    pool: DefiBalance
    token0: DefiBalance
    token1: DefiBalance


def _decode_token(entry) -> DefiBalance:
    decimals = entry[0][3]
    return DefiBalance(
        token_address=entry[0][0],
        token_name=entry[0][1],
        token_symbol=entry[0][2],
        balance=Balance(
            amount=token_normalized_value_decimals(entry[1], decimals),
            usd_value=ZERO,
        ),
    )


def _decode_result(data) -> UniLPBalance:
    pool_token = _decode_token(data[0])
    token0 = _decode_token(data[1][0])
    token1 = _decode_token(data[1][1])
    return UniLPBalance(pool=pool_token, token0=token0, token1=token1)


def token_balances_from_ethereum(
        address: ChecksumEthAddress,
        ethereum: EthereumManager,
        zerion: Zerion,
        lp_addresses: List[ChecksumEthAddress],
):
    """Query uniswap token balances from ethereum

    The number of addresses to query in one call depends a lot on the node used.
    With an infura node we saw the following:
    500 addresses per call took on average 43 seconds for 20450 addresses
    2000 addresses per call took on average 36 seconds for 20450 addresses
    4000 addresses per call took on average 32.6 seconds for 20450 addresses
    5000 addresses timed out a few times
    """
    zerion_contract = EthereumContract(
        address=zerion.contract_address,
        abi=ZERION_ABI,
        deployed_block=0,
    )
    chunks = list(get_chunks(lp_addresses, n=4000))
    balances = []
    for idx, chunk in enumerate(chunks):
        print(f'Querying univ2 token balances for {address} {idx + 1} / {len(chunks)}')
        result = zerion_contract.call(
            ethereum=ethereum,
            method_name='getAdapterBalance',
            arguments=[address, '0x4EdBac5c8cb92878DD3fd165e43bBb8472f34c3f', chunk]
        )

        for entry in result[1]:
            balances.append(_decode_result(entry))

    return balances


def pairs_and_token_details_from_graph() -> Dict[str, Any]:
    """Detect the uniswap v2 pool tokens by using the subgraph"""
    step = 1000
    querystr = """
      pairs(first:$first, skip: $skip) {
        id
        token0{
          id
          symbol
          name
          decimals
        }
        token1{
          id
          symbol
          name
          decimals
        }
      }
    }
    """
    param_types = {'$first': 'Int!', '$skip': 'Int!'}
    param_values = {'first': step, 'skip': 0}
    graph = Graph('https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2')

    contracts = []
    total_pairs_num = 0
    while True:
        print(f'Querying graph pairs batch {param_values["skip"]} - {param_values["skip"] + step}')
        result = graph.query(querystr, param_types=param_types, param_values=param_values)
        for entry in result['pairs']:
            contracts.append({
                'address': to_checksum_address(entry['id']),
                'token0': {
                    'address': to_checksum_address(entry['token0']['id']),
                    'name': entry['token0']['name'],
                    'symbol': entry['token0']['symbol'],
                    'decimals': int(entry['token0']['decimals']),
                },
                'token1': {
                    'address': to_checksum_address(entry['token1']['id']),
                    'name': entry['token1']['name'],
                    'symbol': entry['token1']['symbol'],
                    'decimals': int(entry['token1']['decimals']),
                },
            })

        pairs_num = len(result['pairs'])
        total_pairs_num += pairs_num
        if pairs_num < step:
            break

        param_values['skip'] = total_pairs_num

    return contracts


def write_result_to_file(result: Any, name: str) -> None:
    filepath = root_path / 'rotkehlchen' / 'data' / name
    filepath.touch(exist_ok=True)
    with filepath.open(mode="w") as f:
        f.write(json.dumps(result))


def read_file_if_exists(name: str) -> Optional[Dict[str, Any]]:
    filepath = root_path / 'rotkehlchen' / 'data' / name
    data = None
    if filepath.exists():
        with filepath.open(mode='r') as f:
            data = json.loads(f.read())

    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='Uniswap LP tokens address extractor',
        description=(
            'A tool to retrieve all addresses and details of uniswap v2 LP tokens '
            'using multiple data sources. Both an ethereum node and the subgraph'
        ),
    )
    parser.add_argument(
        '--eth-rpc-endpoint',
        help='The eth rpc endpoint',
    )
    parser.add_argument(
        '--use-other-nodes',
        action='store_true',
        help='If given then other open nodes are also used',
    )
    parser.add_argument(
        '--source',
        help='The source to use. If both then result of 1 verifies the other',
        choices=['ethereum', 'graph', 'both'],
    )
    parser.add_argument(
        '--force-query',
        help='Even if the results have been saved in a file requery',
        action='store_true',
    )
    args = parser.parse_args()

    results = {}
    if args.source in ('graph', 'both'):
        saved_data = read_file_if_exists('uniswap_lp_tokens_graph.json')
        if saved_data and args.force_query is False:
            results['graph'] = saved_data
        else:
            result = pairs_and_token_details_from_graph()
            results['graph'] = result
            write_result_to_file(result, 'uniswap_lp_tokens_graph.json')

    if args.source in ('ethereum', 'both'):
        ethereum, zerion = init_ethereum(
            rpc_endpoint=args.eth_rpc_endpoint,
            use_other_nodes=args.use_other_nodes,
        )
        saved_data = read_file_if_exists('uniswap_lp_tokens_ethereum.json')
        if saved_data and args.force_query is False:
            results['ethereum'] = saved_data
        else:
            result = pairs_from_ethereum(ethereum)
            results['ethereum'] = result
            write_result_to_file(result, 'uniswap_lp_tokens_ethereum.json')

        start = ts_now()
        balances = token_balances_from_ethereum(
            address='0x1554d34D46842778999cB4eb1381b19f651e4a9d',
            ethereum=ethereum,
            zerion=zerion,
            lp_addresses=results['ethereum'],
        )
        end = ts_now()
        print(f'Querying balances took {end-start} seconds')
        print(balances)

    if args.source == 'both':
        for entry in results['graph']:
            assert entry['address'] in results['ethereum']
