from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID, ChecksumEvmAddress

if TYPE_CHECKING:
    from eth_typing import ABI

CPT_FLUID: Final = 'fluid'
FLUID_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_FLUID,
    label='Fluid',
    image='fluid.svg',
)

FLUID_SUPPORTED_CHAINS: Final = (
    ChainID.ETHEREUM,
    ChainID.ARBITRUM_ONE,
    ChainID.BASE,
    ChainID.POLYGON_POS,
    ChainID.BINANCE_SC,
)

# FluidLiquidity and FluidVaultFactory share identical CREATE2 addresses across all supported
# EVM deployments (https://docs.fluid.instadapp.io/).
FLUID_LIQUIDITY: Final = string_to_evm_address('0x52Aa899454998Be5b000Ad077a46Bbe360F4e497')
FLUID_VAULT_FACTORY: Final = string_to_evm_address('0x324c5Dc1fC42c7a4D43d92df1eBA58a54d13Bf2d')

FLUID_VAULT_RESOLVER_L2: Final = string_to_evm_address(
    '0xA5C3E16523eeeDDcC34706b0E6bE88b4c6EA95cC',
)
FLUID_VAULT_RESOLVERS: Final[dict[ChainID, ChecksumEvmAddress]] = {
    ChainID.ETHEREUM: string_to_evm_address('0x6943Ed9E53e3713Bf24a92016984254311772F1A'),
    ChainID.ARBITRUM_ONE: FLUID_VAULT_RESOLVER_L2,
    ChainID.BASE: FLUID_VAULT_RESOLVER_L2,
    ChainID.POLYGON_POS: FLUID_VAULT_RESOLVER_L2,
    ChainID.BINANCE_SC: FLUID_VAULT_RESOLVER_L2,
}

FLUID_DEX_RESOLVER_COMMON: Final = string_to_evm_address(
    '0x11D80CfF056Cef4F9E6d23da8672fE9873e5cC07',
)
FLUID_DEX_RESOLVERS: Final[dict[ChainID, ChecksumEvmAddress]] = {
    ChainID.ETHEREUM: FLUID_DEX_RESOLVER_COMMON,
    ChainID.ARBITRUM_ONE: FLUID_DEX_RESOLVER_COMMON,
    ChainID.BASE: FLUID_DEX_RESOLVER_COMMON,
    ChainID.POLYGON_POS: FLUID_DEX_RESOLVER_COMMON,
    ChainID.BINANCE_SC: string_to_evm_address('0xAf572EfC84d905926F7b05C1B7bE04e4E89542B0'),
}

# Event LogOperate(address,address,int256,int256,address,address,uint256,uint256)
LIQUIDITY_LOG_OPERATE: Final = b'M\x93\xb22\xa2N\x82\xb2\x84\xce\xd7F\x1b\xf4\xde\xac\xff\xe6gY\xd5\xc2E\x13\xe6\xf2\x9eW\x1a\xd7\x8d\x15'  # 0x4d93b232a24e82b284ced7461bf4deacffe66759d5c24513e6f29e571ad78d15  # noqa: E501
# Event NewPositionMinted(address,address,uint256)
NEW_POSITION_MINTED: Final = b"\xfc\xc2'\x83S\xc4\xcc]T\xb7B\xd7\xee\xe2\xd4\xa7\xab\xc2.M\xc6!3@\x08\x82\x93\x86\rP+Q"  # 0xfcc2278353c4cc5d54b742d7eee2d4a7abc22e4dc6213340088293860d502b51  # noqa: E501
# Event LogOperate(address,uint256,int256,int256,address)
VAULT_LOG_OPERATE: Final = b'\xfe\xf6G`\xe3\nA\xb9\xd5\xba}\xd6_\xf7#ja\xd8\x9e\xd8\xb4Lg\xa2\x9e\x84\xdb\x1agQ:\x1c'  # 0xfef64760e30a41b9d5ba7dd65ff7236a61d89ed8b44c67a29e84db1a67513a1c  # noqa: E501
# Event LogLiquidate(address,uint256,uint256,address)
VAULT_LOG_LIQUIDATE: Final = b'\x80\xfd\x9c\xc6\xb1\x82\x1fJQ\x0eE\xff\xcehR\xea4\x04\x80{]=\x83?\xfa\x85fD\x08\xaf\xcbf'  # 0x80fd9cc6b1821f4a510e45ffce6852ea3404807b5d3d833ffa85664408afcb66  # noqa: E501

# FluidDexT1 collateral and debt liquidity events for T2/T3/T4 smart vaults:
# Non-perfect events carry (amount0, amount1, shares) with shares in data[64:96].
# Event LogDepositColLiquidity(uint256,uint256,uint256)
DEX_DEPOSIT_COL: Final = b'\xbf\xea\x92\tz$\x87\xd6\xa5\xcc\xf7\xb7\xad\xc3k`\x02#\x8f1\x06V\x8b\xa45\x97p\xf4\xb6se\xa4'  # 0xbfea92097a2487d6a5ccf7b7adc36b6002238f3106568ba4359770f4b67365a4  # noqa: E501
# Event LogWithdrawColLiquidity(uint256,uint256,uint256)
DEX_WITHDRAW_COL: Final = b'\xb6\x1c\x7f;#\xfe\x935\xccljnp6EwXG\x08w\xe6\x1a\x19\xa5\xb4\x92N\x1f\xf8(\x96$'  # 0xb61c7f3b23fe9335cc6c6a6e7036457758470877e61a19a5b4924e1ff8289624  # noqa: E501
# Event LogBorrowDebtLiquidity(uint256,uint256,uint256)
DEX_BORROW_DEBT: Final = b'\x7f\x81B{\xedi\x9d\xc7\xe6\x87\xc5\xdd\xae`a\x93)8\x81\x8fy\xfc\x0eh\x90=U\xefu\xcaEa'  # 0x7f81427bed699dc7e687c5ddae6061932938818f79fc0e68903d55ef75ca4561  # noqa: E501
# Event LogPaybackDebtLiquidity(uint256,uint256,uint256)
DEX_PAYBACK_DEBT: Final = b'\xb6\x9f\x15*pR\x07\x03\xfez\xb4\x87*\x0c\xb3\x92\x83\x86\xb6\x8c\xf3\xc6\xc8<]\x1f\xc0\x8d\x19i\x91\xe8'  # 0xb69f152a70520703fe7ab4872a0cb3928386b68cf3c6c83c5d1fc08d196991e8  # noqa: E501

# Perfect / single-token DEX events carry (shares, token0Amt, token1Amt) with shares in data[0:32].
# Event LogDepositPerfectColLiquidity(uint256,uint256,uint256)
DEX_DEPOSIT_PERFECT_COL: Final = b'%Vr\xef\xfa=\x8b\xa4n@\x9f\xc9d\xae3+\x84\xd3\x10{\xa3\xa5\tk"sF\x06Q\x95(\xa3'  # 0x255672effa3d8ba46e409fc964ae332b84d3107ba3a5096b22734606519528a3  # noqa: E501
# Event LogWithdrawPerfectColLiquidity(uint256,uint256,uint256)
DEX_WITHDRAW_PERFECT_COL: Final = b'o\x83ur\xc1\xefn\x01\n\x84\x1f\xf98\xd5\x93\xec\x05I\x84\xfe\xfe)\xdf*\x064\xbb\xf0\x1fM\xb3['  # 0x6f837572c1ef6e010a841ff938d593ec054984fefe29df2a0634bbf01f4db35b  # noqa: E501
# Event LogWithdrawColInOneToken(uint256,uint256,uint256)
DEX_WITHDRAW_COL_ONE_TOKEN: Final = b'\xc9\x8f7\x91N\x06\xdb6\xc1\x86THM\xb8\\K\xb8dWZ\x1b\x9f\x81\x81\x13?\xf3=\xea-4\xf3'  # 0xc98f37914e06db36c18654484db85c4bb864575a1b9f8181133ff33dea2d34f3  # noqa: E501
# Event LogBorrowPerfectDebtLiquidity(uint256,uint256,uint256)
DEX_BORROW_PERFECT_DEBT: Final = b'Hm\x99\x19G\xa8\x85\x80\x13\x0f\xf5\xac\xd9\xecT\xdc7\xfb\x8d\xa4\xbfj\xb7\x88q\xd5\xcdo\xa5\x81m\xf7'  # 0x486d991947a88580130ff5acd9ec54dc37fb8da4bf6ab78871d5cd6fa5816df7  # noqa: E501
# Event LogPaybackPerfectDebtLiquidity(uint256,uint256,uint256)
DEX_PAYBACK_PERFECT_DEBT: Final = b'\x03\xb7{D\xc2\xfe\x88\x16\xd5Z.O\x90\xa8u8\xc4\x8dAH\xe3R$\xc0pI\xfd#\x04\xfa:0'  # 0x03b77b44c2fe8816d55a2e4f90a87538c48d4148e35224c07049fd2304fa3a30  # noqa: E501
# Event LogPaybackDebtInOneToken(uint256,uint256,uint256)
DEX_PAYBACK_DEBT_ONE_TOKEN: Final = b'\x97\xdf\xa8L\xbf\xfc\xf6[\x8d\x03O\x05t9G+\xc98h\xa6l\xc0\xe7(\xc2\xfa\xff\xb0\x0f\x8bI#'  # 0x97dfa84cbffcf65b8d034f057439472bc93868a66cc0e728c2faffb00f8b4923  # noqa: E501

DEX_SHARES_LAST_COL_TOPICS: Final = frozenset({DEX_DEPOSIT_COL, DEX_WITHDRAW_COL})
DEX_SHARES_FIRST_COL_TOPICS: Final = frozenset({
    DEX_DEPOSIT_PERFECT_COL,
    DEX_WITHDRAW_PERFECT_COL,
    DEX_WITHDRAW_COL_ONE_TOKEN,
})
DEX_SHARES_LAST_DEBT_TOPICS: Final = frozenset({DEX_BORROW_DEBT, DEX_PAYBACK_DEBT})
DEX_SHARES_FIRST_DEBT_TOPICS: Final = frozenset({
    DEX_BORROW_PERFECT_DEBT,
    DEX_PAYBACK_PERFECT_DEBT,
    DEX_PAYBACK_DEBT_ONE_TOKEN,
})

VAULT_FACTORY_ABI: Final[ABI] = [{'inputs': [{'name': 'vault_', 'type': 'address'}], 'name': 'isVault', 'outputs': [{'name': '', 'type': 'bool'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501
VAULT_CONSTANTS_ABI: Final[ABI] = [{'inputs': [], 'name': 'constantsView', 'outputs': [{'components': [{'name': 'liquidity', 'type': 'address'}, {'name': 'factory', 'type': 'address'}, {'name': 'operateImplementation', 'type': 'address'}, {'name': 'adminImplementation', 'type': 'address'}, {'name': 'secondaryImplementation', 'type': 'address'}, {'name': 'deployer', 'type': 'address'}, {'name': 'supply', 'type': 'address'}, {'name': 'borrow', 'type': 'address'}, {'components': [{'name': 'token0', 'type': 'address'}, {'name': 'token1', 'type': 'address'}], 'name': 'supplyToken', 'type': 'tuple'}, {'components': [{'name': 'token0', 'type': 'address'}, {'name': 'token1', 'type': 'address'}], 'name': 'borrowToken', 'type': 'tuple'}, {'name': 'vaultId', 'type': 'uint256'}, {'name': 'vaultType', 'type': 'uint256'}, {'name': 'supplyExchangePriceSlot', 'type': 'bytes32'}, {'name': 'borrowExchangePriceSlot', 'type': 'bytes32'}, {'name': 'userSupplySlot', 'type': 'bytes32'}, {'name': 'userBorrowSlot', 'type': 'bytes32'}], 'name': 'constantVariables', 'type': 'tuple'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501
VAULT_RESOLVER_ABI: Final[ABI] = [{'inputs': [{'name': 'user_', 'type': 'address'}], 'name': 'positionsByUser', 'outputs': [{'components': [{'name': 'nftId', 'type': 'uint256'}, {'name': 'owner', 'type': 'address'}, {'name': 'isLiquidated', 'type': 'bool'}, {'name': 'isSupplyPosition', 'type': 'bool'}, {'name': 'tick', 'type': 'int256'}, {'name': 'tickId', 'type': 'uint256'}, {'name': 'beforeSupply', 'type': 'uint256'}, {'name': 'beforeBorrow', 'type': 'uint256'}, {'name': 'beforeDustBorrow', 'type': 'uint256'}, {'name': 'supply', 'type': 'uint256'}, {'name': 'borrow', 'type': 'uint256'}, {'name': 'dustBorrow', 'type': 'uint256'}], 'name': 'userPositions_', 'type': 'tuple[]'}, {'components': [{'name': 'vault', 'type': 'address'}, {'name': 'isSmartCol', 'type': 'bool'}, {'name': 'isSmartDebt', 'type': 'bool'}, {'components': [{'name': 'liquidity', 'type': 'address'}, {'name': 'factory', 'type': 'address'}, {'name': 'operateImplementation', 'type': 'address'}, {'name': 'adminImplementation', 'type': 'address'}, {'name': 'secondaryImplementation', 'type': 'address'}, {'name': 'deployer', 'type': 'address'}, {'name': 'supply', 'type': 'address'}, {'name': 'borrow', 'type': 'address'}, {'components': [{'name': 'token0', 'type': 'address'}, {'name': 'token1', 'type': 'address'}], 'name': 'supplyToken', 'type': 'tuple'}, {'components': [{'name': 'token0', 'type': 'address'}, {'name': 'token1', 'type': 'address'}], 'name': 'borrowToken', 'type': 'tuple'}, {'name': 'vaultId', 'type': 'uint256'}, {'name': 'vaultType', 'type': 'uint256'}, {'name': 'supplyExchangePriceSlot', 'type': 'bytes32'}, {'name': 'borrowExchangePriceSlot', 'type': 'bytes32'}, {'name': 'userSupplySlot', 'type': 'bytes32'}, {'name': 'userBorrowSlot', 'type': 'bytes32'}], 'name': 'constantVariables', 'type': 'tuple'}, {'components': [{'name': 'supplyRateMagnifier', 'type': 'uint16'}, {'name': 'borrowRateMagnifier', 'type': 'uint16'}, {'name': 'collateralFactor', 'type': 'uint16'}, {'name': 'liquidationThreshold', 'type': 'uint16'}, {'name': 'liquidationMaxLimit', 'type': 'uint16'}, {'name': 'withdrawalGap', 'type': 'uint16'}, {'name': 'liquidationPenalty', 'type': 'uint16'}, {'name': 'borrowFee', 'type': 'uint16'}, {'name': 'oracle', 'type': 'address'}, {'name': 'oraclePriceOperate', 'type': 'uint256'}, {'name': 'oraclePriceLiquidate', 'type': 'uint256'}, {'name': 'rebalancer', 'type': 'address'}, {'name': 'lastUpdateTimestamp', 'type': 'uint256'}], 'name': 'configs', 'type': 'tuple'}, {'components': [{'name': 'lastStoredLiquiditySupplyExchangePrice', 'type': 'uint256'}, {'name': 'lastStoredLiquidityBorrowExchangePrice', 'type': 'uint256'}, {'name': 'lastStoredVaultSupplyExchangePrice', 'type': 'uint256'}, {'name': 'lastStoredVaultBorrowExchangePrice', 'type': 'uint256'}, {'name': 'liquiditySupplyExchangePrice', 'type': 'uint256'}, {'name': 'liquidityBorrowExchangePrice', 'type': 'uint256'}, {'name': 'vaultSupplyExchangePrice', 'type': 'uint256'}, {'name': 'vaultBorrowExchangePrice', 'type': 'uint256'}, {'name': 'supplyRateLiquidity', 'type': 'uint256'}, {'name': 'borrowRateLiquidity', 'type': 'uint256'}, {'name': 'supplyRateVault', 'type': 'int256'}, {'name': 'borrowRateVault', 'type': 'int256'}, {'name': 'rewardsOrFeeRateSupply', 'type': 'int256'}, {'name': 'rewardsOrFeeRateBorrow', 'type': 'int256'}], 'name': 'exchangePricesAndRates', 'type': 'tuple'}, {'components': [{'name': 'totalSupplyVault', 'type': 'uint256'}, {'name': 'totalBorrowVault', 'type': 'uint256'}, {'name': 'totalSupplyLiquidityOrDex', 'type': 'uint256'}, {'name': 'totalBorrowLiquidityOrDex', 'type': 'uint256'}, {'name': 'absorbedSupply', 'type': 'uint256'}, {'name': 'absorbedBorrow', 'type': 'uint256'}], 'name': 'totalSupplyAndBorrow', 'type': 'tuple'}, {'components': [{'name': 'withdrawLimit', 'type': 'uint256'}, {'name': 'withdrawableUntilLimit', 'type': 'uint256'}, {'name': 'withdrawable', 'type': 'uint256'}, {'name': 'borrowLimit', 'type': 'uint256'}, {'name': 'borrowableUntilLimit', 'type': 'uint256'}, {'name': 'borrowable', 'type': 'uint256'}, {'name': 'borrowLimitUtilization', 'type': 'uint256'}, {'name': 'minimumBorrowing', 'type': 'uint256'}], 'name': 'limitsAndAvailability', 'type': 'tuple'}, {'components': [{'name': 'totalPositions', 'type': 'uint256'}, {'name': 'topTick', 'type': 'int256'}, {'name': 'currentBranch', 'type': 'uint256'}, {'name': 'totalBranch', 'type': 'uint256'}, {'name': 'totalBorrow', 'type': 'uint256'}, {'name': 'totalSupply', 'type': 'uint256'}, {'components': [{'name': 'status', 'type': 'uint256'}, {'name': 'minimaTick', 'type': 'int256'}, {'name': 'debtFactor', 'type': 'uint256'}, {'name': 'partials', 'type': 'uint256'}, {'name': 'debtLiquidity', 'type': 'uint256'}, {'name': 'baseBranchId', 'type': 'uint256'}, {'name': 'baseBranchMinima', 'type': 'int256'}], 'name': 'currentBranchState', 'type': 'tuple'}], 'name': 'vaultState', 'type': 'tuple'}, {'components': [{'name': 'modeWithInterest', 'type': 'bool'}, {'name': 'supply', 'type': 'uint256'}, {'name': 'withdrawalLimit', 'type': 'uint256'}, {'name': 'lastUpdateTimestamp', 'type': 'uint256'}, {'name': 'expandPercent', 'type': 'uint256'}, {'name': 'expandDuration', 'type': 'uint256'}, {'name': 'baseWithdrawalLimit', 'type': 'uint256'}, {'name': 'withdrawableUntilLimit', 'type': 'uint256'}, {'name': 'withdrawable', 'type': 'uint256'}, {'name': 'decayEndTimestamp', 'type': 'uint256'}, {'name': 'decayAmount', 'type': 'uint256'}], 'name': 'liquidityUserSupplyData', 'type': 'tuple'}, {'components': [{'name': 'modeWithInterest', 'type': 'bool'}, {'name': 'borrow', 'type': 'uint256'}, {'name': 'borrowLimit', 'type': 'uint256'}, {'name': 'lastUpdateTimestamp', 'type': 'uint256'}, {'name': 'expandPercent', 'type': 'uint256'}, {'name': 'expandDuration', 'type': 'uint256'}, {'name': 'baseBorrowLimit', 'type': 'uint256'}, {'name': 'maxBorrowLimit', 'type': 'uint256'}, {'name': 'borrowableUntilLimit', 'type': 'uint256'}, {'name': 'borrowable', 'type': 'uint256'}, {'name': 'borrowLimitUtilization', 'type': 'uint256'}], 'name': 'liquidityUserBorrowData', 'type': 'tuple'}], 'name': 'vaultsData_', 'type': 'tuple[]'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501
DEX_RESOLVER_ABI: Final[ABI] = [{'inputs': [{'name': 'dex_', 'type': 'address'}], 'name': 'getDexState', 'outputs': [{'components': [{'name': 'lastToLastStoredPrice', 'type': 'uint256'}, {'name': 'lastStoredPrice', 'type': 'uint256'}, {'name': 'centerPrice', 'type': 'uint256'}, {'name': 'lastUpdateTimestamp', 'type': 'uint256'}, {'name': 'lastPricesTimeDiff', 'type': 'uint256'}, {'name': 'oracleCheckPoint', 'type': 'uint256'}, {'name': 'oracleMapping', 'type': 'uint256'}, {'name': 'totalSupplyShares', 'type': 'uint256'}, {'name': 'totalBorrowShares', 'type': 'uint256'}, {'name': 'isSwapAndArbitragePaused', 'type': 'bool'}, {'components': [{'name': 'isRangeChangeActive', 'type': 'bool'}, {'name': 'isThresholdChangeActive', 'type': 'bool'}, {'name': 'isCenterPriceShiftActive', 'type': 'bool'}, {'components': [{'name': 'oldUpper', 'type': 'uint256'}, {'name': 'oldLower', 'type': 'uint256'}, {'name': 'duration', 'type': 'uint256'}, {'name': 'startTimestamp', 'type': 'uint256'}, {'name': 'oldTime', 'type': 'uint256'}], 'name': 'rangeShift', 'type': 'tuple'}, {'components': [{'name': 'oldUpper', 'type': 'uint256'}, {'name': 'oldLower', 'type': 'uint256'}, {'name': 'duration', 'type': 'uint256'}, {'name': 'startTimestamp', 'type': 'uint256'}, {'name': 'oldTime', 'type': 'uint256'}], 'name': 'thresholdShift', 'type': 'tuple'}, {'components': [{'name': 'shiftPercentage', 'type': 'uint256'}, {'name': 'duration', 'type': 'uint256'}, {'name': 'startTimestamp', 'type': 'uint256'}], 'name': 'centerPriceShift', 'type': 'tuple'}], 'name': 'shifts', 'type': 'tuple'}, {'name': 'token0PerSupplyShare', 'type': 'uint256'}, {'name': 'token1PerSupplyShare', 'type': 'uint256'}, {'name': 'token0PerBorrowShare', 'type': 'uint256'}, {'name': 'token1PerBorrowShare', 'type': 'uint256'}], 'name': 'state_', 'type': 'tuple'}], 'stateMutability': 'nonpayable', 'type': 'function'}]  # noqa: E501
