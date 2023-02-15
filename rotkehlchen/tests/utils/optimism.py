from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.constants import ONE
from rotkehlchen.types import SupportedBlockchain

OPTIMISM_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED: tuple[str, list[tuple]] = (
    'optimism_manager_connect_at_start',
    [(WeightedNode(
        node_info=NodeName(
            name='own',
            endpoint='https://mainnet.optimism.io',
            owned=False,
            blockchain=SupportedBlockchain.OPTIMISM,
        ),
        active=True,
        weight=ONE,
    ), WeightedNode(
        node_info=NodeName(
            name='node real',
            # does not offer archive nodes for optimism
            # https://docs.nodereal.io/docs/archive-node
            endpoint='https://opt-mainnet.nodereal.io/v1/e85935b614124789b99aa92930aca9a4',
            owned=True,
            blockchain=SupportedBlockchain.OPTIMISM,
        ),
        active=True,
        weight=ONE,
    ), WeightedNode(
        node_info=NodeName(
            name='blast api',
            endpoint='https://optimism-mainnet.public.blastapi.io',
            owned=True,
            blockchain=SupportedBlockchain.OPTIMISM,
        ),
        active=True,
        weight=ONE,
    ), WeightedNode(
        node_info=NodeName(
            name='ankr',
            endpoint='https://rpc.ankr.com/optimism',
            owned=False,
            blockchain=SupportedBlockchain.OPTIMISM,
        ),
        active=True,
        weight=ONE,
    ))],
)
