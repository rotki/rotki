import { balanceKeys } from '@/services/consts';
import { OverviewDefiProtocol } from '@/store/defi/types';

const FINNEXUS = 'FinNexus';
const PICKLE_FINANCE = 'Pickle Finance';
const PICKLE_FINANCE_FARMS = 'Pickle Finance • Farms';
const PICKLE_FINANCE_STAKING = 'Pickle Finance • Staking';
const DODO = 'DODO';
const BEREZKA = 'Berezka';
const BZX = 'bZx';
const CREAM = 'C.R.E.A.M.';
const CREAM_STAKING = 'C.R.E.A.M. • Staking';
const SWERVE = 'Swerve';
const SWERVE_LIQUIDITY_GAUGES = 'Swerve • Liquidity Gauges';
const SASHIMISWAP = 'SashimiSwap';
const HARVEST = 'Harvest';
const KIMCHI = 'KIMCHI';
const SUSHISWAP = 'SushiSwap';
const NEXUS_MUTUAL = 'Nexus Mutual';
const MOONISWAP = 'Mooniswap';
const MATIC = 'Matic';
const ARAGON = 'Aragon';
export const AAVE = 'Aave';
const AAVE_STAKING = 'Aave • Staking';
const AAVE_UNISWAPMARKET = 'Aave • Uniswap Market';
const BALANCER = 'Balancer';
export const COMPOUND = 'Compound';
const COMPOUND_GOVERNANCE = 'Compound Governance';
const CURVE = 'Curve';
const CURVE_VESTING = 'Curve • Vesting';
const CURVE_LIQUIDITY_GAUGES = 'Curve • Liquidity Gauges';
const DYDX = 'dYdX';
const MELON = 'Melon';
export const YEARN_FINANCE_VAULTS = 'yearn.finance • Vaults';
const KEEPERDAO = 'KeeperDAO';
const MSTABLE = 'mStable';
const MSTABLE_STAKING = 'mStable • Staking';
const KYBERDAO = 'KyberDAO';
const DDEX_SPOT = 'DDEX • Spot';
const DDEX_MARGIN = 'DDEX • Margin';
const DDEX_LENDING = 'DDEX • Lending';
const AMPLEFORTH = 'Ampleforth';
const MAKER_GOVERNANCE = 'Maker Governance';
const GNOSIS_PROTOCOL = 'Gnosis Protocol';
const UNISWAPV2 = 'Uniswap V2';
const IDLE = 'Idle';
const IDLE_RISKADJUSTED = 'Idle • Risk-Adjusted';
const PIEDAO = 'PieDAO';
const MULTICOLLATERAL_DAI = 'Multi-Collateral Dai';
const BANCOR = 'Bancor';
const DEFI_MONEY_MARKET = 'DeFi Money Market';
const TOKENSETS = 'TokenSets';
const UNISWAPV1 = 'Uniswap V1';
const SYNTHETIX = 'Synthetix';
const POOLTOGETHER = 'PoolTogether';
const DAI_SAVINGS_RATE = 'Dai Savings Rate';
const CHAI = 'Chai';
const IEARNFINANCEV3 = 'iearn.finance (v3)';
const IEARNFINANCEV2 = 'iearn.finance (v2)';
const YGOVFINANCEV1 = 'ygov.finance (v1)';
const YGOVFINANCEV2 = 'ygov.finance (v2)';
const ZEROX_STAKING = '0x Staking';
const CHIGASTOKEN = 'Chi Gastoken by 1inch';
const ZLOTFINANCE = 'zlot.finance';
export const MAKERDAO = 'MakerDAO';
const AAVE_V2 = 'Aave V2';
const AAVE_V2_VARIABLE_DEBT = 'Aave V2 • Variable Debt';
const AAVE_V2_STABLE_DEBT = 'Aave V2 • Stable Debt';
const SNOW_SWAP = 'SnowSwap';
const HARVEST_PROFIT_SHARING = 'Harvest • Profit Sharing';
const IDLE_EARLY_REWARDS = 'Idle • Early Rewards';

export const OVERVIEW_PROTOCOLS = [
  YGOVFINANCEV1,
  YGOVFINANCEV2,
  ZLOTFINANCE,
  FINNEXUS,
  PICKLE_FINANCE,
  PICKLE_FINANCE_FARMS,
  PICKLE_FINANCE_STAKING,
  DODO,
  BEREZKA,
  BZX,
  CREAM,
  CREAM_STAKING,
  SWERVE,
  SWERVE_LIQUIDITY_GAUGES,
  SASHIMISWAP,
  HARVEST,
  KIMCHI,
  SUSHISWAP,
  NEXUS_MUTUAL,
  MOONISWAP,
  MATIC,
  ARAGON,
  MELON,
  YEARN_FINANCE_VAULTS,
  KEEPERDAO,
  MSTABLE,
  MSTABLE_STAKING,
  KYBERDAO,
  DDEX_SPOT,
  DDEX_MARGIN,
  DDEX_LENDING,
  AMPLEFORTH,
  MAKER_GOVERNANCE,
  GNOSIS_PROTOCOL,
  CHIGASTOKEN,
  UNISWAPV2,
  PIEDAO,
  MULTICOLLATERAL_DAI,
  BANCOR,
  DEFI_MONEY_MARKET,
  TOKENSETS,
  ZEROX_STAKING,
  UNISWAPV1,
  SYNTHETIX,
  POOLTOGETHER,
  DAI_SAVINGS_RATE,
  CHAI,
  IEARNFINANCEV3,
  IEARNFINANCEV2,
  IDLE,
  IDLE_RISKADJUSTED,
  DYDX,
  CURVE,
  CURVE_VESTING,
  CURVE_LIQUIDITY_GAUGES,
  COMPOUND,
  COMPOUND_GOVERNANCE,
  BALANCER,
  AAVE,
  AAVE_STAKING,
  AAVE_UNISWAPMARKET,
  MAKERDAO,
  AAVE_V2,
  AAVE_V2_VARIABLE_DEBT,
  AAVE_V2_STABLE_DEBT,
  SNOW_SWAP,
  HARVEST_PROFIT_SHARING,
  IDLE_EARLY_REWARDS
] as const;

const ICON_LIST: { [protocol in OverviewDefiProtocol]: string } = {
  [ZLOTFINANCE]: 'zlotfinance.png',
  [YGOVFINANCEV1]: 'iearn.png',
  [YGOVFINANCEV2]: 'iearn.png',
  [ZEROX_STAKING]: '0x_staking.svg',
  [AAVE]: 'aave.svg',
  [AAVE_V2]: 'aave.svg',
  [AAVE_STAKING]: 'aave.svg',
  [AAVE_UNISWAPMARKET]: 'aave.svg',
  [AMPLEFORTH]: 'ampl.svg',
  [ARAGON]: 'aragon.svg',
  [BALANCER]: 'balancer.svg',
  [BANCOR]: 'bancor.svg',
  [BEREZKA]: 'berezka.png',
  [BZX]: 'bzx.svg',
  [CHAI]: 'chai.png',
  [CHIGASTOKEN]: 'chi.png',
  [COMPOUND]: 'compound.svg',
  [COMPOUND_GOVERNANCE]: 'compound.svg',
  [CREAM]: 'cream.svg',
  [CREAM_STAKING]: 'cream.svg',
  [CURVE]: 'curve.svg',
  [CURVE_VESTING]: 'curve.svg',
  [CURVE_LIQUIDITY_GAUGES]: 'curve.svg',
  [MULTICOLLATERAL_DAI]: 'dai.svg',
  [DDEX_LENDING]: 'ddex.svg',
  [DDEX_SPOT]: 'ddex.svg',
  [DDEX_MARGIN]: 'ddex.svg',
  [DEFI_MONEY_MARKET]: 'dmm.svg',
  [DODO]: 'dodo.svg',
  [DAI_SAVINGS_RATE]: 'makerdao.svg',
  [DYDX]: 'dydx.svg',
  [FINNEXUS]: 'finnexus.svg',
  [GNOSIS_PROTOCOL]: 'gnosis_protocol.png',
  [HARVEST]: 'harvest.gif',
  [IDLE]: 'idle.svg',
  [IDLE_RISKADJUSTED]: 'idle.svg',
  [IEARNFINANCEV2]: 'iearn.png',
  [IEARNFINANCEV3]: 'iearn.png',
  [KEEPERDAO]: 'keeperdao.svg',
  [KIMCHI]: 'kimchi.webp',
  [KYBERDAO]: 'kyber.svg',
  [MAKER_GOVERNANCE]: 'makerdao.svg',
  [MATIC]: 'matic.svg',
  [MELON]: 'melon.svg',
  [MOONISWAP]: 'mooniswap.svg',
  [MSTABLE]: 'mstable.png',
  [MSTABLE_STAKING]: 'mstable.png',
  [NEXUS_MUTUAL]: 'nexusmutual.svg',
  [PICKLE_FINANCE]: 'pickle.png',
  [PICKLE_FINANCE_FARMS]: 'pickle.png',
  [PICKLE_FINANCE_STAKING]: 'pickle.png',
  [PIEDAO]: 'piedao.png',
  [POOLTOGETHER]: 'pooltogether.svg',
  [SASHIMISWAP]: 'sashimi.png',
  [TOKENSETS]: 'set.svg',
  [SUSHISWAP]: 'sushi.png',
  [SWERVE]: 'swerve.png',
  [SWERVE_LIQUIDITY_GAUGES]: 'swerve.png',
  [SYNTHETIX]: 'synthetix.svg',
  [UNISWAPV1]: 'uniswap.svg',
  [UNISWAPV2]: 'uniswap.svg',
  [YEARN_FINANCE_VAULTS]: 'yearn_vaults.svg',
  [MAKERDAO]: 'makerdao.svg',
  [AAVE_V2_VARIABLE_DEBT]: 'aave.svg',
  [AAVE_V2_STABLE_DEBT]: 'aave.svg',
  [SNOW_SWAP]: 'snowswap.svg',
  [HARVEST_PROFIT_SHARING]: 'harvest.gif',
  [IDLE_EARLY_REWARDS]: 'idle.svg'
};

export function getProtcolIcon(name: OverviewDefiProtocol): string {
  return ICON_LIST[name] ?? '';
}

export const UNISWAP_EVENT_MINT = 'mint';
export const UNISWAP_EVENT_BURN = 'burn';

export const UNISWAP_EVENT_TYPE = [
  UNISWAP_EVENT_MINT,
  UNISWAP_EVENT_BURN
] as const;

export const uniswapNumericKeys = [
  ...balanceKeys,
  'usd_price',
  'total_amount',
  'total_supply'
];

export const uniswapTradeNumericKeys = [
  'amount',
  'fee',
  'rate',
  'amount0_in',
  'amount0_out',
  'amount1_in',
  'amount1_out'
];

export const uniswapEventsNumericKeys = [
  'amount0',
  'amount1',
  'lp_amount',
  'usd_price',
  'profit_loss0',
  'profit_loss1',
  'usd_profit_loss'
];
