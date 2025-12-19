from collections.abc import Sequence
from typing import Final

from eth_typing import ABI, ABIEvent

from rotkehlchen.chain.decoding.types import CounterpartyDetails

CPT_THEGRAPH: Final = 'thegraph'
THEGRAPH_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_THEGRAPH,
    label='The Graph',
    image='thegraph.svg',
)
GRAPH_TOKEN_LOCK_WALLET_ABI: Final[ABI] = [{'inputs': [], 'name': 'beneficiary', 'outputs': [{'name': '', 'type': 'address'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501
GRAPH_DELEGATION_TRANSFER_ABI: Final[Sequence[ABIEvent]] = [{'anonymous': False, 'inputs': [{'indexed': True, 'name': 'delegator', 'type': 'address'}, {'indexed': True, 'name': 'l2Delegator', 'type': 'address'}, {'indexed': True, 'name': 'indexer', 'type': 'address'}, {'indexed': False, 'name': 'l2Indexer', 'type': 'address'}, {'indexed': False, 'name': 'transferredDelegationTokens', 'type': 'uint256'}], 'name': 'DelegationTransferredToL2', 'type': 'event'}]  # noqa: E501
TOPIC_STAKE_DELEGATED: Final = b'\xcd\x03f\xdc\xe5$}\x87O\xfc`\xa7b\xaaz\xbb\xb8,\x16\x95\xbb\xb1q`\x9c\x1b\x88a\xe2y\xebs'  # noqa: E501
TOPIC_STAKE_DELEGATED_LOCKED: Final = b'\x040\x18?\x84\xd9\xc4P#\x86\xd4\x99\xda\x80eC\xde\xe1\xd9\xde\x83\xc0\x8b\x01\xe3\x9am!\x16\xc4;%'  # noqa: E501
TOPIC_STAKE_DELEGATED_WITHDRAWN: Final = b'\x1b.w7\xe0C\xc5\xcf\x1bX|\xebM\xae\xb7\xae\x00\x14\x8b\x9b\xda\x8fy\xf1\t>\xea\xd0\x8f\x14\x19R'  # noqa: E501
TOPIC_STAKE_DELEGATED_HORIZON: Final = b'#x\x18\xaf\x8b\xb4w\x10\x14.\xdd\x8f\xc3\x01\xfb\xc5\x07\x06O\xb3W\xcf\x12/\xb1a\xcaD~<\xb1>'  # noqa: E501
TOPIC_STAKE_DELEGATED_LOCKED_HORIZON: Final = b'\x05%\xd6\xad\x1a\xa7\x8a\xbcW\x1b\\\x19\x84\xb5\xe1\xeaO\x14\x126\x8c\x1c\xc3H\xca@\x8d\xbb\x10\x85\xc9\xa1'  # noqa: E501
TOPIC_STAKE_DELEGATED_WITHDRAWN_HORIZON: Final = b'0_Q\x9d\x89\t\xc6v\xff\xd8pI]Ec\x03.\xb0\xb5\x06\x89\x1am\xd9\x82t\x90%l\xc9\x91N'  # noqa: E501
TOPIC_THAW_REQUEST_CREATED: Final = b"\x03e8\xdfJY\x1a\\\xc7Kh\xcf\xc7\xf8\xc6\x1e\x81s\xdb\xc8\x16'\xe1\xd6&\x00\xb6\x1e\x82\x04ax"  # noqa: E501
