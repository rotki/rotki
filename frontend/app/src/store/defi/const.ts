import { balanceKeys } from '@/services/consts';
import { OverviewDefiProtocol } from '@/store/defi/types';

const FINNEXUS = 'FinNexus';
const PICKLE_FINANCE = 'Pickle Finance';
const DODO = 'DODO';
const BEREZKA = 'Berezka';
const BZX = 'bZx';
const CREAM = 'C.R.E.A.M.';
const SWERVE = 'Swerve';
const SASHIMISWAP = 'SashimiSwap';
const HARVEST = 'Harvest';
const KIMCHI = 'KIMCHI';
const SUSHISWAP = 'SushiSwap';
const NEXUS_MUTUAL = 'Nexus Mutual';
const MOONISWAP = 'Mooniswap';
const MATIC = 'Matic';
const ARAGON = 'Aragon';
export const AAVE = 'Aave';
const BALANCER = 'balancer';
export const COMPOUND = 'Compound';
const COMPOUND_COMP = 'Compound Governance';
const CURVE = 'Curve';
const DYDX = 'dYdX';
const MELON = 'Melon';
export const YEARN_FINANCE_VAULTS = 'yearn.finance • Vaults';
const KEEPERDAO = 'KeeperDAO';
const MSTABLE = 'mStable';
const KYBERDAO = 'KyberDAO';
const DDEX_SPOT = 'DDEX • Spot';
const DDEX_MARGIN = 'DDEX • Margin';
const DDEX_LENDING = 'DDEX • Lending';
const AMPLEFORTH = 'Ampleforth';
const MAKER_GOVERNANCE = 'Maker Governance';
const GNOSIS_PROTOCOL = 'Gnosis Protocol';
const UNISWAPV2 = 'Uniswap V2';
const AAVE_UNISWAPMARKET = 'Aave • Uniswap Market';
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
const IDLE_BESTYIELD = 'Idle • Best-Yield';
const ZEROX_STAKING = '0x Staking';
const CHIGASTOKEN = 'Chi Gastoken by 1inch';
export const MAKERDAO = 'MakerDAO';

export const OVERVIEW_PROTOCOLS = [
  FINNEXUS,
  PICKLE_FINANCE,
  DODO,
  BEREZKA,
  BZX,
  CREAM,
  SWERVE,
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
  KYBERDAO,
  DDEX_SPOT,
  DDEX_MARGIN,
  DDEX_LENDING,
  AMPLEFORTH,
  MAKER_GOVERNANCE,
  GNOSIS_PROTOCOL,
  CHIGASTOKEN,
  IDLE_RISKADJUSTED,
  AAVE_UNISWAPMARKET,
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
  IDLE_BESTYIELD,
  DYDX,
  CURVE,
  COMPOUND,
  COMPOUND_COMP,
  BALANCER,
  AAVE,
  MAKERDAO
] as const;

const ICON_LIST: { [protocol in OverviewDefiProtocol]: string } = {
  [ZEROX_STAKING]: '0x_staking.svg',
  [AAVE]: 'aave.svg',
  [AAVE_UNISWAPMARKET]: 'aave.svg',
  [AMPLEFORTH]: 'ampl.svg',
  [ARAGON]: 'aragon.svg',
  [BALANCER]: 'balancer.svg',
  [BANCOR]: 'bancor.svg',
  [BEREZKA]: '',
  [BZX]: 'bzx.svg',
  [CHAI]: 'chai.png',
  [CHIGASTOKEN]: 'chi.png',
  [COMPOUND]: 'compound.svg',
  [COMPOUND_COMP]: 'compound.svg',
  [CREAM]: 'cream.svg',
  [CURVE]: 'curve.svg',
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
  [IDLE_BESTYIELD]: 'idle.svg',
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
  [NEXUS_MUTUAL]: 'nexusmutual.svg',
  [PICKLE_FINANCE]: 'pickle.png',
  [PIEDAO]: 'piedao.png',
  [POOLTOGETHER]: 'pooltogether.svg',
  [SASHIMISWAP]: 'sashimi.png',
  [TOKENSETS]: 'set.svg',
  [SUSHISWAP]: 'sushi.png',
  [SWERVE]: 'swerve.png',
  [SYNTHETIX]: 'synthetix.svg',
  [UNISWAPV1]: 'uniswap.svg',
  [UNISWAPV2]: 'uniswap.svg',
  [YEARN_FINANCE_VAULTS]: 'yearn_vaults.svg',
  [MAKERDAO]: 'makerdao.svg'
};

export function getProtcolIcon(name: OverviewDefiProtocol): string {
  return ICON_LIST[name];
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
