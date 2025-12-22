from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.defi.zerionsdk import ZERION_ADAPTER_ADDRESS
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import LiquidityPool
from rotkehlchen.chain.ethereum.interfaces.ammswap.utils import decode_result
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.types import WeightedNode
from rotkehlchen.constants import ONE
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import get_chunks

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler


def uniswap_lp_token_balances(
        userdb: 'DBHandler',
        address: ChecksumEvmAddress,
        ethereum: 'EthereumInquirer',
        lp_addresses: list[ChecksumEvmAddress],
) -> list[LiquidityPool]:
    """Query uniswap token balances from ethereum chain

    The number of addresses to query in one call depends a lot on the node used.
    With an infura node we saw the following:
    500 addresses per call took on average 43 seconds for 20450 addresses
    2000 addresses per call took on average 36 seconds for 20450 addresses
    4000 addresses per call took on average 32.6 seconds for 20450 addresses
    5000 addresses timed out a few times
    """
    zerion_contract = EvmContract(
        address=ZERION_ADAPTER_ADDRESS,
        abi=ethereum.contracts.abi('ZERION_ADAPTER'),
        deployed_block=1586199170,
    )
    if (own_node_info := ethereum.get_own_node_info()) is not None:
        chunks = list(get_chunks(lp_addresses, n=4000))
        call_order = [WeightedNode(node_info=own_node_info, weight=ONE, active=True)]
    else:
        chunks = list(get_chunks(lp_addresses, n=700))
        call_order = ethereum.default_call_order(skip_indexers=True)

    balances = []
    for chunk in chunks:
        result = zerion_contract.call(
            node_inquirer=ethereum,
            method_name='getAdapterBalance',
            arguments=[address, '0x4EdBac5c8cb92878DD3fd165e43bBb8472f34c3f', chunk],
            call_order=call_order,
        )
        balances = [decode_result(userdb, entry) for entry in result[1]]

    return balances
