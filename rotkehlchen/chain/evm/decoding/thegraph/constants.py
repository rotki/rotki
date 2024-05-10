from typing import Final
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails

CPT_THEGRAPH: Final = 'thegraph'
THEGRAPH_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_THEGRAPH,
    label='The Graph',
    image='thegraph.svg',
)

GRAPH_DELEGATION_TRANSFER_ABI: Final = [
    {
        'anonymous': 'false',
        'inputs': [
            {
                'indexed': 'true',
                'internalType': 'address',
                'name': 'delegator',
                'type': 'address',
            },
            {
                'indexed': 'true',
                'internalType': 'address',
                'name': 'l2Delegator',
                'type': 'address',
            },
            {
                'indexed': 'true',
                'internalType': 'address',
                'name': 'indexer',
                'type': 'address',
            },
            {
                'indexed': 'false',
                'internalType': 'address',
                'name': 'l2Indexer',
                'type': 'address',
            },
            {
                'indexed': 'false',
                'internalType': 'uint256',
                'name': 'transferredDelegationTokens',
                'type': 'uint256',
            },
        ],
        'name': 'DelegationTransferredToL2',
        'type': 'event',
    },
]
