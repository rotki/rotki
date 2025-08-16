from typing import Final

from eth_typing import ABI

CPT_VELODROME: Final = 'velodrome'
CPT_AERODROME: Final = 'aerodrome'
SWAP_V2: Final = b'\xb3\xe2w6\x06\xab\xfd6\xb5\xbd\x919K:T\xd19\x836\xc6P\x05\xba\xf7\xbfz\x05\xef\xef\xfa\xf7['  # noqa: E501
REMOVE_LIQUIDITY_EVENT_V2: Final = b']bJ\xa9\xc1H\x15:\xb3Dl\x1b\x15Of\x0e\xe7p\x1eT\x9f\xe9\xb6-\xabqq\xb1\xc8\x0eo\xa2'  # Burn event (burns LP tokens)  # noqa: E501
GAUGE_DEPOSIT_V2: Final = b'UH\xc87\xab\x06\x8c\xf5j,$y\xdf\x08\x82\xa4\x92/\xd2\x03\xed\xb7Qs!\x83\x1d\x95\x07\x8c_b'  # noqa: E501
CLAIM_REWARDS_V2: Final = b"\x1f\x89\xf9c3\xd3\x130\x00\xeeDts\x15\x1f\xa9`eC6\x8f\x02'\x1c\x9d\x95\xae\x14\xf1;\xccg"  # noqa: E501
VOTING_ESCROW_WITHDRAW: Final = b"\x02\xf2Rp\xa4\xd8{\xeau\xdbT\x1c\xdf\xe5Y3J'[J#5 \xedl\n$)f|\xca\x94"  # noqa: E501
VOTING_ESCROW_CREATE_LOCK: Final = b'\x885\xc2*\x0cu\x11\x88\xde\x86h\x1e\x15\x90B#\xc0T\xbe\xdd\\h\xec\x88X\x94[x1)\x02s'  # noqa: E501
VOTING_ESCROW_METADATA_UPDATE: Final = b"\xf8\xe1\xa1Z\xba\x93\x98\xe0\x19\xf0\xb4\x9d\xf1\xa4\xfd\xe9\x8e\xe1z\xe3E\xcb_k^,'\xf5\x03>\x8c\xe7"  # noqa: E501
VOTER_CLAIM_REWARDS: Final = b'\x9a\xa0[=p\xa9\xe3\xe2\xf0\x04\xf09d\x889V\x05v3O\xb4\\\x81\xf9\x1bm\xb0:\xd9\xe2\xef\xc9'  # noqa: E501
VOTER_VOTED: Final = b'E-D\x0e\xfc0\xdf\xa1J\x0e\xf8\x03\xcc\xb5Y6\xaf\x86\x0e\xc6\xa6\x96\x0e\xd2\x7f\x12\x9b\xef\x91?)j'  # noqa: E501
VOTING_ESCROW_ABI: ABI = [{'inputs': [{'name': '_tokenId', 'type': 'uint256'}], 'name': 'locked', 'outputs': [{'components': [{'name': 'amount', 'type': 'int128'}, {'name': 'end', 'type': 'uint256'}, {'name': 'isPermanent', 'type': 'bool'}], 'name': '', 'type': 'tuple'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501
