from collections.abc import Sequence
from typing import Final

from eth_typing import ABIEvent

from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails

CPT_THEGRAPH: Final = 'thegraph'
THEGRAPH_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_THEGRAPH,
    label='The Graph',
    image='thegraph.svg',
)

GRAPH_DELEGATION_TRANSFER_ABI: Final[Sequence[ABIEvent]] = [
    {  # all type ignores are due to inability of typing to see ABIComponentIndexed
        'anonymous': False,
        'inputs': [
            {
                'indexed': True,  # type: ignore
                'name': 'delegator',
                'type': 'address',
            },
            {
                'indexed': True,  # type: ignore
                'name': 'l2Delegator',
                'type': 'address',
            },
            {
                'indexed': True,  # type: ignore
                'name': 'indexer',
                'type': 'address',
            },
            {
                'indexed': False,  # type: ignore
                'name': 'l2Indexer',
                'type': 'address',
            },
            {
                'indexed': False,  # type: ignore
                'name': 'transferredDelegationTokens',
                'type': 'uint256',
            },
        ],
        'name': 'DelegationTransferredToL2',
        'type': 'event',
    },
]
