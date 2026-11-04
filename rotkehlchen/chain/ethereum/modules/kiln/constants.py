from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from eth_typing.abi import ABI

CPT_KILN: Final = 'kiln'
KILN_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_KILN,
    label='Kiln',
    image='kiln.svg',
    darkmode_image='kiln_dark.svg',
)

# Pooled staking integration contracts. Each partner (wallet/custodian) gets its own one,
# which mints its own receipt token at the same address. Integration contracts that are not
# listed here are still detected at decoding time, see KilnDecoder._is_kiln_integration.
KILN_INTEGRATION_CONTRACTS: Final = {
    string_to_evm_address('0x5DB5235b5C7e247488784986e58019fFFd98FdA4'),  # Ledger Live psETH
    string_to_evm_address('0x437636e4b984EAe19045626AA269a89f906cf96c'),  # Crypto.com DeFi Wallet cdwETH  # noqa: E501
    string_to_evm_address('0x30a4aa1d14D44f0f5BFe887447AB6FAcc94A549F'),  # Coinbase Wallet cbwsETH
    string_to_evm_address('0x2401c39d7ba9E283668a53fcC7B8F5FD9e716fdf'),  # ocsETH
    string_to_evm_address('0x42ECf9Bde9078D659663Da66b97c4823f762005e'),  # CoolWallet cwstETH
    string_to_evm_address('0x5b1c9Ee05794E9667806F1Bd1C6Ae6D196498183'),  # Giddy Wallet GiddyETH
    string_to_evm_address('0xba1613Cf1fF0d7307315f1D98465E27877AD3f02'),  # MEW MEWcbETH
    string_to_evm_address('0xe5fAA3FCc7729C3Ac7b4571207bb5978e5c33e81'),  # Veno VenoKilnETH
    string_to_evm_address('0xC4DCB059dD98B45B090Da8982234C61D0b9e84f9'),  # lcETH
    string_to_evm_address('0xEb4d67DBa18b3bE04484dFC7B7c2780E8D32A79d'),  # Edge edgeETH
    string_to_evm_address('0x61Ac42269d0035cD86c52b6c5bB299DAa73c7135'),  # Bitnovo bnETH
    string_to_evm_address('0x4D893E724a0a913F6fb6Ca1581644DbD81Dcd5Bd'),  # xPortal xpsETH
    string_to_evm_address('0x9F4e700A0D532beE981cD40Cb9753956b12355bD'),  # Ellipal elpETH
}
# The exit queues of the operator pools (vPool) the integration contracts deposit into.
# The exit queue is also the ERC721 contract of the exit tickets.
KILN_EXIT_QUEUES: Final = {
    string_to_evm_address('0x8d6Fd650500f82c7D978a440348e5a9b886943bF'),  # Kiln operator pool
    string_to_evm_address('0x86358F7B33b599c484e0335B8Ee4f7f7f92d8b60'),  # Coinbase Cloud operator pool  # noqa: E501
}

# Every vPool and vExitQueue is a beacon proxy spawned by the Kiln Nexus and they all share
# the same two beacons. Reading the beacon slot is how unknown contracts are verified as Kiln.
EIP1967_BEACON_SLOT: Final = 0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50
KILN_VPOOL_BEACON: Final = string_to_evm_address('0x1D6103243d0507a9d1314bAC09379Bf57a5CF155')
KILN_EXIT_QUEUE_BEACON: Final = string_to_evm_address('0x24a1DFEbAEc4e501c2152a5E4A434B236FCE3D3B')

STAKE_TOPIC: Final = b'"\x06N;\xa8\x80d\xd7\x1f\xf2\x11\xd5P\xf2\xb1\xf3\xe6;\x19\xeb?\xd6GTN!\xc8\xf6\xe5\xcc\xc4.'  # noqa: E501  # 0x22064e3ba88064d71ff211d550f2b1f3e63b19eb3fd647544e21c8f6e5ccc42e
EXIT_TOPIC: Final = b'u\xaa\x83\xb9\x13C9\x8b\xcf\xa38\xc4\x01|)x\x0f$\xe0\x17\x8b\xb7\x96\x994Sth\x01\xd8\x0b\x03'  # noqa: E501  # 0x75aa83b91343398bcfa338c4017c29780f24e0178bb796993453746801d80b03
PRINTED_TICKET_TOPIC: Final = b'\x00\x80\xdfE\xf1!\x86\x85m\xa4\x84\xa1IK\xb5\x19\x07\xe2\xab\xecZ\xbc\x9a@\x1eD<\x11k\xedq\xa5'  # noqa: E501  # 0x0080df45f12186856da484a1494bb51907e2abec5abc9a401e443c116bed71a5
FILLED_TICKET_TOPIC: Final = b'\xef:\xbb\x81\x9e1\xc9\x00\x93\x02691\xf92\x86\xb38\xda|\xab\x0c%\xe6\xf9H\xc7\x95_\xd5\xfdD'  # noqa: E501  # 0xef3abb819e31c9009302363931f93286b338da7cab0c25e6f948c7955fd5fd44
PAYMENT_TOPIC: Final = b'\xd4\xf49u\xfe\xb8\x9fH\xdd0\xca\xbb\xb3 \x11\x04[\xe1\x87\xd1\xe1\x1c\x8e\xa9\xfa\xa4>\xfc5(%\x19'  # noqa: E501  # 0xd4f43975feb89f48dd30cabbb32011045be187d1e11c8ea9faa43efc35282519

KILN_INTEGRATION_ABI: Final[ABI] = [{
    'inputs': [],
    'name': 'pools',
    'outputs': [{'name': '', 'type': 'address[]'}],
    'stateMutability': 'view',
    'type': 'function',
}, {
    'inputs': [],
    'name': 'rate',
    'outputs': [{'name': '', 'type': 'uint256'}],
    'stateMutability': 'view',
    'type': 'function',
}]
KILN_EXIT_QUEUE_ABI: Final[ABI] = [{
    'inputs': [{'name': 'id', 'type': 'uint256'}],
    'name': 'ticket',
    'outputs': [{
        'components': [
            {'name': 'position', 'type': 'uint128'},
            {'name': 'size', 'type': 'uint128'},
            {'name': 'maxExitable', 'type': 'uint128'},
        ],
        'name': '',
        'type': 'tuple',
    }],
    'stateMutability': 'view',
    'type': 'function',
}, {
    'inputs': [{'name': 'tokenId', 'type': 'uint256'}],
    'name': 'ownerOf',
    'outputs': [{'name': '', 'type': 'address'}],
    'stateMutability': 'view',
    'type': 'function',
}]
