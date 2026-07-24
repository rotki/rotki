from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from eth_typing import ABI

CPT_YEARN_VESTING: Final = 'yearn-vesting'
YEARN_VESTING_LABEL: Final = 'Yearn vesting'

# All the yearn vesting escrow factories deployed on ethereum mainnet.
# https://github.com/yearn/yearn-vesting-escrow#production-deployments
VESTING_FACTORY_V1: Final = string_to_evm_address('0xF124534bfa6Ac7b89483B401B4115Ec0d27cad6A')
VESTING_FACTORY_V2: Final = string_to_evm_address('0x98d3872b4025ABE58C4667216047Fe549378d90f')
VESTING_FACTORY_V3: Final = string_to_evm_address('0x200C92Dd85730872Ab6A1e7d5E40A067066257cF')
VESTING_FACTORY_V4: Final = string_to_evm_address('0xFbd94e2D6942D5b4Ed0C5C9C43bded77a8f20215')

# vyperlang.eth -- receives the optional donation of the v0.3.0 factory deployments
VYPER_DONATION_ADDRESS: Final = string_to_evm_address('0x70CCBE10F980d80b7eBaab7D2E3A73e87D67B775')

# VestingEscrowCreated(address indexed funder, address indexed token, address indexed recipient, address escrow, uint256 amount, uint256 vesting_start, uint256 vesting_duration, uint256 cliff_length) emitted by the v0.1.0/v0.2.0 factories  # noqa: E501
VESTING_ESCROW_CREATED_TOPIC: Final = b'M\x92O+\xe6\xd9\r\xa8;\xe4|\xa6\xbc<\x90\xe0\xf5\xc5\xe3e\xd7\xe9y\x7f\xae\xb4\xb9\xf8#PZx'  # noqa: E501
# VestingEscrowCreated(address indexed funder, address indexed token, address indexed recipient, address escrow, uint256 amount, uint256 vesting_start, uint256 vesting_duration, uint256 cliff_length, bool open_claim) emitted by the v0.3.0 factory  # noqa: E501
VESTING_ESCROW_CREATED_V3_TOPIC: Final = b'\x99\xfd\x02\xdb\xc6YD\x92?w\xd3\xe5\xd3\xe7~\x8cL\x1b@& \x1b\xe5DZ\x8e\x82q\x83\xe9\x93\xe2'  # noqa: E501
# TokenVestingEscrowCreated(address indexed escrow, address indexed token, address indexed recipient, address funder, address revoker, uint256 amount, uint256 vesting_start, uint256 vesting_duration, uint256 cliff_length, bool permissionless_claims) emitted by the v0.4.0 factory  # noqa: E501
TOKEN_VESTING_ESCROW_CREATED_V4_TOPIC: Final = b"\xf8\xeaS\xac'}\x19\x995\x94x\xd9c\x81\xcf\xbdE\x9d\xa6\x012\xda\xc1\x17B\x0c\xfe\x8b\xe8\xb3\x8b\x02"  # noqa: E501
# RugPull(address recipient, uint256 rugged) emitted by the v0.1.0/v0.2.0 escrows
RUG_PULL_TOPIC: Final = b'&\xc3\x92\x10\xac\x9c\xda$jl\xc6\xe3=\xa6|\x19q\xd5\xf1K\xbc2\xe2\xb6l>\x14\xab\x815I\xd7'  # noqa: E501
# Revoked(address recipient, address owner, uint256 rugged, uint256 ts) emitted by the v0.3.0 escrows  # noqa: E501
REVOKED_V3_TOPIC: Final = b'BZ\x9dQ\xf6W5W\x00\xbaAjN\x9e`j#\xb8\xc5\x83\x1a\x99$A\xdd\xf4%Den:\x8e'  # noqa: E501
# Revoked(address indexed recipient, address indexed revoker, address indexed receiver, uint256 unvested_amount, uint256 ts) emitted by the v0.4.0 escrows  # noqa: E501
REVOKED_V4_TOPIC: Final = b'\xf1\r\xb8\xb5O\x9b \x04\x00~\x7fcL\x90p\xfe\xb6g\xaf\x03\x04A\xda\x00\x07\xb8\x83\x90u\x8a\xc5['  # noqa: E501

# The escrows are deployed by the factories as proxies to a per-version implementation,
# so the exact runtime bytecode identifies an address as a yearn vesting escrow.
# v0.1.0 uses the old vyper forwarder format while v0.2.0+ use EIP-1167 minimal proxies.
VESTING_ESCROW_PROXY_CODES: Final = frozenset({
    '0x3660006000376110006000366000739c351cabc5d9e1393678d221f84e6ee3d05c016f5af4602c57600080fd5b6110006000f3',  # v0.1.0  # noqa: E501
    '0x363d3d373d3d3d363d73ab080a16007dc2e34b99f269a0217b4e96f888135af43d82803e903d91602b57fd5bf3',  # v0.2.0  # noqa: E501
    '0x363d3d373d3d3d363d739692f652a3048eb7f5074e12b907f20d33f37a015af43d82803e903d91602b57fd5bf3',  # v0.3.0  # noqa: E501
    '0x363d3d373d3d3d363d734cae5c8d3fae0f1e7f005975cbfc0df1d4c323885af43d82803e903d91602b57fd5bf3',  # v0.4.0  # noqa: E501
})

VESTING_ESCROW_ABI: Final[ABI] = [
    {
        'inputs': [],
        'name': 'recipient',
        'outputs': [{'name': '', 'type': 'address'}],
        'stateMutability': 'view',
        'type': 'function',
    },
]
