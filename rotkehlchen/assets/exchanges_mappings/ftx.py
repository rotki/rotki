from rotkehlchen.assets.exchanges_mappings.common import COMMON_ASSETS_MAPPINGS
from rotkehlchen.constants.resolver import evm_address_to_identifier, strethaddress_to_identifier
from rotkehlchen.types import ChainID, EvmTokenKind

WORLD_TO_FTX = COMMON_ASSETS_MAPPINGS | {
    strethaddress_to_identifier('0x50D1c9771902476076eCFc8B2A83Ad6b9355a4c9'): 'FTT',
    strethaddress_to_identifier('0xcca0c9c383076649604eE31b20248BC04FdF61cA'): 'ASD',
    'SOL-2': 'SOL',
    'COIN': 'COIN',
    # SLP is smooth love potion
    strethaddress_to_identifier('0xCC8Fa225D80b9c7D42F96e9570156c65D6cAAa25'): 'SLP',
    'MER-2': 'MER',
    strethaddress_to_identifier('0x476c5E26a75bd202a9683ffD34359C0CC15be0fF'): 'SRM',
    strethaddress_to_identifier('0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF'): 'IMX',
    'GENE': 'GENE',
    strethaddress_to_identifier('0xC581b735A1688071A1746c968e0798D642EDE491'): 'EURT',
    'LUNA-2': 'LUNA',
    strethaddress_to_identifier('0x3392D8A60B77F8d3eAa4FB58F09d835bD31ADD29'): 'INDI',
    strethaddress_to_identifier('0xAf5191B0De278C7286d6C7CC6ab6BB8A73bA2Cd6'): 'STG',
    strethaddress_to_identifier('0x5c147e74D63B1D31AA3Fd78Eb229B65161983B2b'): 'WFLOW',
    strethaddress_to_identifier('0x27702a26126e0B3702af63Ee09aC4d1A084EF628'): 'ALEPH',
    evm_address_to_identifier('0x0f2D719407FdBeFF09D87557AbB7232601FD9F29', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SYN',  # noqa: E501
    evm_address_to_identifier('0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LDO',  # noqa: E501
    evm_address_to_identifier('0x08d967bb0134F2d07f7cfb6E246680c53927DD30', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MATH',  # noqa: E501
    evm_address_to_identifier('0xbC396689893D065F41bc2C6EcbeE5e0085233447', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PERP',  # noqa: E501
    evm_address_to_identifier('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SNX',  # noqa: E501
    evm_address_to_identifier('0x090185f2135308BaD17527004364eBcC2D37e5F6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SPELL',  # noqa: E501
    evm_address_to_identifier('0x8CE9137d39326AD0cD6491fb5CC0CbA0e089b6A9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SXP',  # noqa: E501
    evm_address_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'COMP',  # noqa: E501
    evm_address_to_identifier('0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FXS',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0x2ba592F78dB6436527729929AAf6c908497cB200', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CREAM',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0x15D4c048F83bd7e37d49eA4C83a07267Ec4203dA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GALA',  # noqa: E501
    evm_address_to_identifier('0xa1faa113cbE53436Df28FF0aEe54275c13B40975', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALPHA',  # noqa: E501
    evm_address_to_identifier('0xAC51066d7bEC65Dc4589368da368b212745d63E8', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALICE',  # noqa: E501
    evm_address_to_identifier('0x3472A5A71965499acd81997a54BBA8D852C6E53d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BADGER',  # noqa: E501
    evm_address_to_identifier('0x0D8775F648430679A709E98d2b0Cb6250d2887EF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAT',  # noqa: E501
    evm_address_to_identifier('0xAE12C5930881c53715B369ceC7606B70d8EB229f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'C98',  # noqa: E501
    evm_address_to_identifier('0x3845badAde8e6dFF049820680d1F14bD3903a5d0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SAND',  # noqa: E501
    evm_address_to_identifier('0x8e17ed70334C87eCE574C9d537BC153d8609e2a3', ChainID.BINANCE, EvmTokenKind.ERC20): 'WRX',  # noqa: E501
    evm_address_to_identifier('0xD46bA6D942050d489DBd938a2C909A5d5039A161', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AMPL',  # noqa: E501
    evm_address_to_identifier('0xa3BeD4E1c75D00fa6f4E5E6922DB7261B5E9AcD2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MTA',  # noqa: E501
    evm_address_to_identifier('0x43Dfc4159D86F3A37A5A4B3D4580b888ad7d4DDd', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DODO',  # noqa: E501
    evm_address_to_identifier('0xf8C3527CC04340b208C854E985240c02F7B7793f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FRONT',  # noqa: E501
    evm_address_to_identifier('0xd1ba9BAC957322D6e8c07a160a3A8dA11A0d2867', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'HMT',  # noqa: E501
    evm_address_to_identifier('0x3E9BC21C9b189C09dF3eF1B824798658d5011937', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LINA',  # noqa: E501
    evm_address_to_identifier('0x4e352cF164E64ADCBad318C3a1e222E9EBa4Ce42', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MCB',  # noqa: E501
    evm_address_to_identifier('0xff56Cc6b1E6dEd347aA0B7676C85AB0B3D08B0FA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ORBS',  # noqa: E501
    evm_address_to_identifier('0xfc82bb4ba86045Af6F327323a46E80412b91b27d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PROM',  # noqa: E501
    evm_address_to_identifier('0xFE3E6a25e6b192A42a44ecDDCd13796471735ACf', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'REEF',  # noqa: E501
    evm_address_to_identifier('0x0996bFb5D057faa237640E2506BE7B4f9C46de0B', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RNDR',  # noqa: E501
    evm_address_to_identifier('0x888888848B652B3E3a0f34c96E00EEC0F3a23F72', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TLM',  # noqa: E501
    evm_address_to_identifier('0x582d872A1B094FC48F5DE31D3B73F2D9bE47def1', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TONCOIN',  # noqa: E501
    evm_address_to_identifier('0x2C537E5624e4af88A7ae4060C022609376C8D0EB', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TRYB',  # noqa: E501
    evm_address_to_identifier('0x8564653879a18C560E7C0Ea0E084c516C62F5653', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UBXT',  # noqa: E501
    evm_address_to_identifier('0x915044526758533dfB918ecEb6e44bc21632060D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CHR',  # noqa: E501
    evm_address_to_identifier('0x80C62FE4487E1351b47Ba49809EBD60ED085bf52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CLV',  # noqa: E501
    evm_address_to_identifier('0xaaAEBE6Fe48E54f431b0C390CfaF0b017d09D42d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CEL',  # noqa: E501
    evm_address_to_identifier('0xB0c7a3Ba49C7a6EaBa6cD4a96C55a1391070Ac9A', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MAGIC',  # noqa: E501
    evm_address_to_identifier('0x4b13006980aCB09645131b91D259eaA111eaF5Ba', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MYC',  # noqa: E501
}
