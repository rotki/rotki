import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Set

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.contracts import EthereumContract
from rotkehlchen.chain.ethereum.graph import Graph
from rotkehlchen.chain.ethereum.manager import (
    ETHEREUM_NODES_TO_CONNECT_AT_START,
    EthereumManager,
    NodeName,
)
from rotkehlchen.chain.ethereum.uniswap.utils import uniswap_lp_token_balances
from rotkehlchen.chain.ethereum.utils import multicall_specific
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.greenlets import GreenletManager
from rotkehlchen.serialization.deserialize import deserialize_ethereum_address
from rotkehlchen.tests.utils.ethereum import wait_until_all_nodes_connected
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
    return ethereum


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
        try:
            pairs.extend([deserialize_ethereum_address(x[0]) for x in result])
        except DeserializationError:
            print('Error deserializing address while fetching uniswap v2 pool tokens')
            sys.exit(1)

    return pairs


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
            try:
                deserialized_entry = deserialize_ethereum_address(entry['id'])
                deserialized_token_0 = deserialize_ethereum_address(entry['token0']['id'])
                deserialized_token_1 = deserialize_ethereum_address(entry['token1']['id'])
            except DeserializationError:
                print('Error deserializing address while fetching uniswap v2 pool tokens')
                sys.exit(1)

            contracts.append({
                'address': deserialized_entry,
                'token0': {
                    'address': deserialized_token_0,
                    'name': entry['token0']['name'],
                    'symbol': entry['token0']['symbol'],
                    'decimals': int(entry['token0']['decimals']),
                },
                'token1': {
                    'address': deserialized_token_1,
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
    parser.add_argument(
        '--no-query-balances',
        help='Do not query balances, just create the lp tokens file',
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
        ethereum = init_ethereum(
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

        if args.no_query_balances is False:
            database = DBHandler('fill', 'me', ethereum.msg_aggregator, None)
            start = ts_now()
            known_assets: Set[EthereumToken] = set()
            unknown_assets: Set[EthereumToken] = set()
            balances = uniswap_lp_token_balances(
                userdb=database,
                address='0x1554d34D46842778999cB4eb1381b19f651e4a9d',  # test address
                ethereum=ethereum,
                lp_addresses=results['ethereum'],
                known_assets=known_assets,
                unknown_assets=unknown_assets,
            )
            end = ts_now()
            print(f'Querying balances took {end-start} seconds')
            print(balances)

    if args.source == 'both':
        for entry in results['graph']:
            assert entry['address'] in results['ethereum']
