from collections.abc import Sequence
from typing import Final

from eth_typing import ABIEvent

from rotkehlchen.chain.decoding.types import CounterpartyDetails

CPT_THEGRAPH: Final = 'thegraph'
THEGRAPH_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_THEGRAPH,
    label='The Graph',
    image='thegraph.svg',
)

GRAPH_DELEGATION_TRANSFER_ABI: Final[Sequence[ABIEvent]] = [
    {
        'anonymous': False,
        'inputs': [
            {
                'indexed': True,
                'name': 'delegator',
                'type': 'address',
            },
            {
                'indexed': True,
                'name': 'l2Delegator',
                'type': 'address',
            },
            {
                'indexed': True,
                'name': 'indexer',
                'type': 'address',
            },
            {
                'indexed': False,
                'name': 'l2Indexer',
                'type': 'address',
            },
            {
                'indexed': False,
                'name': 'transferredDelegationTokens',
                'type': 'uint256',
            },
        ],
        'name': 'DelegationTransferredToL2',
        'type': 'event',
    },
]
