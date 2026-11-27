from typing import Final, NamedTuple

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID, ChecksumEvmAddress

CPT_SYMBIOSIS: Final = 'symbiosis'
SYMBIOSIS_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_SYMBIOSIS,
    label='Symbiosis',
    image='symbiosis.svg',
)


class SymbiosisDeployment(NamedTuple):
    portal: ChecksumEvmAddress | None
    synthesis: ChecksumEvmAddress | None
    bridge: ChecksumEvmAddress


# Symbiosis Portal event topics
# keccak of SynthesizeRequest(bytes32,address,uint256,address,address,uint256,address)
SYNTHESIZE_REQUEST_TOPIC: Final = b'12_\xe0\xa1\xa2\xe6\xa5\xb1\xe4\x15r\x15k\xa5\xb4\xe9O\x0f\xae~\x7fc\xec!\xe9\xb5\xce\x1eK>\xab'  # noqa: E501
# keccak of BurnCompleted(bytes32,bytes32,address,uint256,uint256,address)
BURN_COMPLETED_TOPIC: Final = b'\xae\xefd\xb7h{\x98Ve\xb6b\x0c\x7f\xa2q\xb6\xf0Q\xa3\xfb\xe2\xbf\xc3f\xfb\x9c\x96F\x02\xebm&'  # noqa: E501
# keccak of RevertSynthesizeCompleted(bytes32,address,uint256,uint256,address)
REVERT_SYNTHESIZE_COMPLETED_TOPIC: Final = b'\xef\xcd\xf9\xeaNeW\x1d,\xe9\xc00\xc4iT\xe9Pf-\xf8\xa7\xd8\xbd\x03\x9f\xc4A~7\xb2\xf8\x8c'  # noqa: E501

# Symbiosis Synthesis event topics
# keccak of BurnRequest(bytes32,address,uint256,address,address,uint256,address)
BURN_REQUEST_TOPIC: Final = b'_\x00\xe8\xf0\xd6\x1f\xf1\x19\t\x12\x87\x99I\x02l\x85\xa8\x1f?\x96\x03\x8c\x7fL\xd8h\xbd\xfe\x88.\x0e\xeb'  # noqa: E501
# keccak of BurnRequestBTC(uint64,address,bytes,uint256,uint256,address)
BURN_REQUEST_BTC_TOPIC: Final = b'v\xa6\xd9~\xe6D\xff\x15:\xa6\xe2*\x0c\t\n\x07\x01.al\x1c\x02Y\xce\x98PY;\x9a\xedS\x16'  # noqa: E501
# keccak of BurnRequestTON(bytes32,address,uint256,address,(int8,bytes32),uint256,address)
BURN_REQUEST_TON_TOPIC: Final = b'\xb2/f\xd5\xcbM\x95\x8c\x8b\xee\xc9\x9fa\x91x$\xd4\x07\xa7ME\x14\xd8\xd4L\xc7rG\xe6zNZ'  # noqa: E501
# keccak of SynthesizeCompleted(bytes32,address,bytes32,uint256,uint256,address)
SYNTHESIZE_COMPLETED_TOPIC: Final = b'\x1f?\x0f<{-\xf4\x80u\\d\x86\xa12\xf2\x15\xe7\xb2\xb8\x9f\xcc\xa0\xbe\xec\xd9Z\x96\x96\xc7\x17\x89\xb6'  # noqa: E501
# keccak of BTCSynthesizeCompleted(bytes32,address,uint256,uint64,uint256,address)
BTC_SYNTHESIZE_COMPLETED_TOPIC: Final = b'\xb6\xaaD\xf5\xb2\xe6\xd2\x03\x06P\xd5QOj\xa3\xc8"\xcd\x88\xce#\xe5\x1f\xe2\x0fep\x83\x7f\x02\x04+'  # noqa: E501
# keccak of RevertBurnCompleted(bytes32,address,uint256,uint256,address)
REVERT_BURN_COMPLETED_TOPIC: Final = b'\xb6\xf5\xf7\xb9\x8c\xc7\x8a\x801\xc9g\xaf\x16:\x8c\x19\x7fG\n5\xdf\x1e2j\x908\x85\x96y\xe6\xa1\x84'  # noqa: E501

# Symbiosis BridgeV2 event topic & selectors used to inspect multi-hop sChain routing
# keccak of OracleRequest(address,bytes,address,address,uint256)
ORACLE_REQUEST_TOPIC: Final = b'S-\xbbm\x06\x1e\xee\x97\xabCp\x06\x0f`\xed\xe1\x0b=\xc3a\xcc\x12\x14\xc0z\xe5\xe3M\xd8nj\xaf'  # noqa: E501
# Selectors for metaMintSyntheticToken and nested finalCalldata calls
META_MINT_SYNTHETIC_TOKEN_SELECTOR: Final = b'\xc2\x9a\x91\xbc'
META_BURN_SYNTHETIC_TOKEN_SELECTOR: Final = b'\xe6k\xb5P'
BURN_SYNTHETIC_TOKEN_SELECTOR: Final = b'\xcb\xef_,'
BURN_SYNTHETIC_TOKEN_BTC_SELECTOR: Final = b'\xa0\xd9Up'
BURN_SYNTHETIC_TOKEN_TON_SELECTOR: Final = b'A\xfa\xbd\x12'

# Symbiosis routing and non-EVM chain IDs (from symbiosis-finance/js-sdk src/constants.ts)
SYMBIOSIS_SCHAIN_ID: Final = 13863860
SYMBIOSIS_LEGACY_SCHAIN_ID: Final = 56288
SYMBIOSIS_SCHAIN_IDS: Final = frozenset((SYMBIOSIS_SCHAIN_ID, SYMBIOSIS_LEGACY_SCHAIN_ID))
SYMBIOSIS_BTC_CHAIN_ID: Final = 3652501241
SYMBIOSIS_SOLANA_CHAIN_ID: Final = 5426
SYMBIOSIS_TON_CHAIN_ID: Final = 85918
SYMBIOSIS_TRON_CHAIN_ID: Final = 728126428
SYMBIOSIS_BCH_CHAIN_ID: Final = 14500145
SYMBIOSIS_DOGE_CHAIN_ID: Final = 300003

# Human-readable labels for well-known Symbiosis chains not in Rotki's ChainID enum.
# Source: symbiosis-finance/js-sdk src/constants.ts
SYMBIOSIS_EXTERNAL_CHAIN_NAMES: Final[dict[int, str]] = {
    SYMBIOSIS_BTC_CHAIN_ID: 'Bitcoin',
    SYMBIOSIS_SOLANA_CHAIN_ID: 'Solana',
    SYMBIOSIS_TON_CHAIN_ID: 'TON',
    SYMBIOSIS_TRON_CHAIN_ID: 'Tron',
    SYMBIOSIS_DOGE_CHAIN_ID: 'Dogecoin',
    SYMBIOSIS_BCH_CHAIN_ID: 'Bitcoin Cash',
    200002: 'Litecoin',
    13300133: 'Zcash',
    12800128: 'Monero',
    14400144: 'XRP Ledger',
    14800148: 'Stellar',
    18150018: 'Cardano',
    78400784: 'Sui',
    9: 'Quai',
    30: 'Rootstock',
    130: 'Unichain',
    169: 'Manta Pacific',
    204: 'opBNB',
    252: 'Fraxtal',
    1088: 'Metis',
    1116: 'Core',
    1329: 'Sei',
    1868: 'Soneium',
    2222: 'Kava',
    2741: 'Abstract',
    2818: 'Morph',
    4200: 'Merlin',
    5000: 'Mantle',
    7000: 'ZetaChain',
    33139: 'ApeChain',
    34443: 'Mode',
    80094: 'Berachain',
    81457: 'Blast',
    167000: 'Taiko',
}

# Symbiosis deployments per supported Rotki EVM chain.
# Source: symbiosis-finance/js-sdk src/crosschain/config/mainnet.ts
SYMBIOSIS_DEPLOYMENTS: Final[dict[ChainID, SymbiosisDeployment]] = {
    ChainID.ETHEREUM: SymbiosisDeployment(
        portal=string_to_evm_address('0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8'),
        synthesis=string_to_evm_address('0xD7c3DF25683871d18BC838E4F619126442Dd38B3'),
        bridge=string_to_evm_address('0x5523985926Aa12BA58DC5Ad00DDca99678D7227E'),
    ),
    ChainID.OPTIMISM: SymbiosisDeployment(
        portal=string_to_evm_address('0x292fC50e4eB66C3f6514b9E402dBc25961824D62'),
        synthesis=None,
        bridge=string_to_evm_address('0x5523985926Aa12BA58DC5Ad00DDca99678D7227E'),
    ),
    ChainID.CRONOS: SymbiosisDeployment(
        portal=string_to_evm_address('0xE75C7E85FE6ADd07077467064aD15847E6ba9877'),
        synthesis=None,
        bridge=string_to_evm_address('0x5523985926Aa12BA58DC5Ad00DDca99678D7227E'),
    ),
    ChainID.BINANCE_SC: SymbiosisDeployment(
        portal=string_to_evm_address('0x5Aa5f7f84eD0E5db0a4a85C3947eA16B53352FD4'),
        synthesis=string_to_evm_address('0x6B1bbd301782FF636601fC594Cd7Bfe74871bfaA'),
        bridge=string_to_evm_address('0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8'),
    ),
    ChainID.GNOSIS: SymbiosisDeployment(
        portal=string_to_evm_address('0x292fC50e4eB66C3f6514b9E402dBc25961824D62'),
        synthesis=None,
        bridge=string_to_evm_address('0x5523985926Aa12BA58DC5Ad00DDca99678D7227E'),
    ),
    ChainID.POLYGON_POS: SymbiosisDeployment(
        portal=string_to_evm_address('0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8'),
        synthesis=None,
        bridge=string_to_evm_address('0x5523985926Aa12BA58DC5Ad00DDca99678D7227E'),
    ),
    ChainID.MONAD: SymbiosisDeployment(
        portal=string_to_evm_address('0x292fC50e4eB66C3f6514b9E402dBc25961824D62'),
        synthesis=None,
        bridge=string_to_evm_address('0x5523985926Aa12BA58DC5Ad00DDca99678D7227E'),
    ),
    ChainID.SONIC: SymbiosisDeployment(
        portal=string_to_evm_address('0xE75C7E85FE6ADd07077467064aD15847E6ba9877'),
        synthesis=None,
        bridge=string_to_evm_address('0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8'),
    ),
    ChainID.BOBA: SymbiosisDeployment(
        portal=string_to_evm_address('0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8'),
        synthesis=None,
        bridge=string_to_evm_address('0x5523985926Aa12BA58DC5Ad00DDca99678D7227E'),
    ),
    ChainID.ZKSYNC_ERA: SymbiosisDeployment(
        portal=string_to_evm_address('0x4f5456d4d0764473DfCA1ffBB8524C151c4F19b9'),
        synthesis=string_to_evm_address('0x07bffC25011901CB01a00127518A154b47eB6e80'),
        bridge=string_to_evm_address('0x51eE73BEC8521E88042b426F31864f456f2a866e'),
    ),
    ChainID.HYPERLIQUID: SymbiosisDeployment(
        portal=string_to_evm_address('0x292fC50e4eB66C3f6514b9E402dBc25961824D62'),
        synthesis=None,
        bridge=string_to_evm_address('0x5523985926Aa12BA58DC5Ad00DDca99678D7227E'),
    ),
    ChainID.BASE: SymbiosisDeployment(
        portal=string_to_evm_address('0xEE981B2459331AD268cc63CE6167b446AF4161f8'),
        synthesis=string_to_evm_address('0x9F6424FE88fBe7785Fa34F0E369F192bF38E7A6e'),
        bridge=string_to_evm_address('0x8097f0B9f06C27AF9579F75762F971D745bb222F'),
    ),
    ChainID.ARBITRUM_ONE: SymbiosisDeployment(
        portal=string_to_evm_address('0x01A3c8E513B758EBB011F7AFaf6C37616c9C24d9'),
        synthesis=string_to_evm_address('0x326adbE46D7E6C1B3927e9309B96DF478bda6D16'),
        bridge=string_to_evm_address('0x5523985926Aa12BA58DC5Ad00DDca99678D7227E'),
    ),
    ChainID.ARBITRUM_NOVA: SymbiosisDeployment(
        portal=string_to_evm_address('0x292fC50e4eB66C3f6514b9E402dBc25961824D62'),
        synthesis=None,
        bridge=string_to_evm_address('0x5523985926Aa12BA58DC5Ad00DDca99678D7227E'),
    ),
    ChainID.AVALANCHE: SymbiosisDeployment(
        portal=string_to_evm_address('0xE75C7E85FE6ADd07077467064aD15847E6ba9877'),
        synthesis=None,
        bridge=string_to_evm_address('0x292fC50e4eB66C3f6514b9E402dBc25961824D62'),
    ),
    ChainID.SCROLL: SymbiosisDeployment(
        portal=string_to_evm_address('0x5Aa5f7f84eD0E5db0a4a85C3947eA16B53352FD4'),
        synthesis=None,
        bridge=string_to_evm_address('0x5523985926Aa12BA58DC5Ad00DDca99678D7227E'),
    ),
}
