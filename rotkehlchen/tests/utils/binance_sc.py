from typing import Final

from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.fval import FVal
from rotkehlchen.types import SupportedBlockchain

ONE_RPC_BINANCE_SC_NODE: Final = NodeName(
    name='1rpc',
    endpoint='https://1rpc.io/bnb',
    owned=False,
    blockchain=SupportedBlockchain.BINANCE_SC,
)

BLASTAPI_BINANCE_SC_NODE: Final = NodeName(
    name='blastapi',
    endpoint='https://bsc-mainnet.public.blastapi.io',
    owned=False,
    blockchain=SupportedBlockchain.BINANCE_SC,
)

LLAMARPC_BINANCE_SC_NODE: Final = NodeName(
    name='llamarpc',
    endpoint='https://binance.llamarpc.com',
    owned=False,
    blockchain=SupportedBlockchain.BINANCE_SC,
)

ANKR_BINANCE_SC_NODE: Final = NodeName(
    name='ankr',
    endpoint='https://rpc.ankr.com/bsc',
    owned=False,
    blockchain=SupportedBlockchain.BINANCE_SC,
)


ZAN_BINANCE_SC_NODE: Final = NodeName(
    name='zan.top',
    endpoint='https://api.zan.top/bsc-mainnet',
    owned=False,
    blockchain=SupportedBlockchain.BINANCE_SC,
)

BINANCE_SC_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED: tuple[str, list[tuple]] = (
    'binance_sc_manager_connect_at_start',
    [(WeightedNode(
        node_info=ONE_RPC_BINANCE_SC_NODE,
        active=True,
        weight=FVal('0.25'),
    ),), (WeightedNode(
        node_info=BLASTAPI_BINANCE_SC_NODE,
        active=True,
        weight=FVal('0.25'),
    ),), (WeightedNode(
        node_info=LLAMARPC_BINANCE_SC_NODE,
        active=True,
        weight=FVal('0.25'),
    ),), (WeightedNode(
        node_info=ANKR_BINANCE_SC_NODE,
        active=True,
        weight=FVal('0.25'),
    ),)],
)
