import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict

from eth_utils.address import to_checksum_address
from web3 import Web3
from web3._utils.abi import get_abi_output_types

from rotkehlchen.chain.ethereum.graph import Graph
from rotkehlchen.chain.ethereum.manager import (
    ETHEREUM_NODES_TO_CONNECT_AT_START,
    EthereumManager,
    NodeName,
)
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.greenlets import GreenletManager
from rotkehlchen.tests.utils.ethereum import wait_until_all_nodes_connected
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import get_chunks

root_path = Path(__file__).resolve().parent.parent.parent


def pairs_from_ethereum(rpcendpoint: str, use_other_nodes: bool) -> Dict[str, Any]:
    """Detect the uniswap v2 pool tokens by using an ethereum node"""
    nodes_to_connect = ETHEREUM_NODES_TO_CONNECT_AT_START if use_other_nodes else (NodeName.OWN,)
    msg_aggregator = MessagesAggregator()
    etherscan = Etherscan(database=None, msg_aggregator=msg_aggregator)
    api_key = os.environ.get('ETHERSCAN_API_KEY', None)
    greenlet_manager = GreenletManager(msg_aggregator=msg_aggregator)
    etherscan.api_key = api_key
    ethereum = EthereumManager(
        ethrpc_endpoint=rpcendpoint,
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

    contracts_file = Path(__file__).resolve().parent / 'contracts.json'
    with contracts_file.open('r') as f:
        contracts = json.loads(f.read())

    factory = contracts['UNISWAPV2FACTORY']
    multicall = contracts['ETH_MULTICALL']
    web3 = Web3()
    pairs_num = ethereum.call_contract(
        contract_address=factory['address'],
        abi=factory['abi'],
        method_name='allPairsLength',
    )
    contract = web3.eth.contract(address=factory['address'], abi=factory['abi'])
    chunks = list(get_chunks(list(range(pairs_num)), n=500))
    pairs = []
    for idx, chunk in enumerate(chunks):
        print(f'Querying univ2 pairs chunk {idx + 1} / {len(chunks)}')
        calls = [(factory['address'], contract.encodeABI('allPairs', args=[i])) for i in chunk]
        multicall_result = ethereum.call_contract(
            contract_address=multicall['address'],
            abi=multicall['abi'],
            method_name='aggregate',
            arguments=[calls],
        )
        block, output = multicall_result
        for x in output:
            fn_abi = contract._find_matching_fn_abi(
                fn_identifier='allPairs',
                args=[1],
            )
            output_types = get_abi_output_types(fn_abi)
            output_data = web3.codec.decode_abi(output_types, x)

            pairs.append(to_checksum_address(output_data[0]))

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
    args = parser.parse_args()

    results = {}
    if args['source'] in ('graph', 'both'):
        result = pairs_and_token_details_from_graph()
        results['graph'] = result
        write_result_to_file(result, 'uniswap_lp_tokens_graph.json')

    if args['source'] in ('ethereum', 'both'):
        result = pairs_from_ethereum(
            rpc_endpoint=args['eth_rpc_endpoint'],
            use_other_nodes=args['use_other_nodes'],
        )
        results['ethereum'] = result
        write_result_to_file(result, 'uniswap_lp_tokens_ethereum.json')

    if args['source'] == 'both':
        for entry in results['graph']:
            assert entry['address'] in results['ethereum']
