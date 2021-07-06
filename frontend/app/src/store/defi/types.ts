import { default as BigNumber } from 'bignumber.js';
import {
  CollateralAssetType,
  DefiBalanceType,
  DSRMovementType,
  EventType,
  MakerDAOVaultEventType,
  SupportedDefiProtocols
} from '@/services/defi/types';
import {
  AaveBalances,
  AaveBorrowingRates,
  AaveHistory,
  AaveHistoryEvents,
  AaveHistoryTotal
} from '@/services/defi/types/aave';
import {
  CompoundBalances,
  CompoundEventType,
  CompoundHistory
} from '@/services/defi/types/compound';
import { UniswapAsset, UniswapBalances } from '@/services/defi/types/uniswap';
import {
  YearnEventType,
  YearnVaultsBalances,
  YearnVaultsHistory
} from '@/services/defi/types/yearn';
import { TradeType } from '@/services/history/types';
import { Balance, HasBalance } from '@/services/types-api';
import {
  AIRDROP_POAP,
  AIRDROPS,
  OVERVIEW_PROTOCOLS,
  UNISWAP_EVENT_TYPE
} from '@/store/defi/const';

export type OverviewDefiProtocol = typeof OVERVIEW_PROTOCOLS[number];

export interface DefiState {
  balancerEvents: BalancerEvents;
  balancerTrades: DexTrades;
  balancerBalances: BalancerBalances;
  dsrHistory: DSRHistory;
  dsrBalances: DSRBalances;
  makerDAOVaults: MakerDAOVault[];
  makerDAOVaultDetails: MakerDAOVaultDetails[];
  aaveBalances: AaveBalances;
  aaveHistory: AaveHistory;
  allProtocols: AllDefiProtocols;
  compoundBalances: CompoundBalances;
  compoundHistory: CompoundHistory;
  yearnVaultsBalances: YearnVaultsBalances;
  yearnVaultsHistory: YearnVaultsHistory;
  yearnVaultsV2Balances: YearnVaultsBalances;
  yearnVaultsV2History: YearnVaultsHistory;
  uniswapBalances: UniswapBalances;
  uniswapTrades: DexTrades;
  uniswapEvents: UniswapEvents;
  airdrops: Airdrops;
}

export interface PoapDeliveryDetails {
  readonly amount: string;
  readonly link: string;
  readonly name: string;
  readonly event: string;
}

export interface Airdrop {
  readonly address: string;
  readonly source: AirdropType;
  readonly amount?: string;
  readonly link?: string;
  readonly asset?: string;
  readonly details?: PoapDeliveryDetails[];
}

export interface AirdropDetail {
  readonly amount: string;
  readonly asset: string;
  readonly link: string;
}

export interface PoapDelivery {
  readonly assets: number[];
  readonly event: string;
  readonly link: string;
  readonly name: string;
}

type AirdropDetails = RegularAirdrop & PoapDetails;

type RegularAirdrop = {
  readonly [source in Exclude<AirdropType, 'poap'>]?: AirdropDetail;
};

type PoapDetails = {
  readonly [AIRDROP_POAP]?: PoapDelivery[];
};

export interface Airdrops {
  readonly [address: string]: AirdropDetails;
}

export type AirdropType = typeof AIRDROPS[number];

export interface DSRBalances {
  readonly currentDsr: BigNumber;
  readonly balances: {
    [account: string]: {
      amount: BigNumber;
      usdValue: BigNumber;
    };
  };
}

interface DSRHistoryItem {
  readonly gainSoFar: Balance;
  readonly movements: DSRMovement[];
}

export interface DSRHistory {
  readonly [address: string]: DSRHistoryItem;
}

interface DSRMovement {
  readonly movementType: DSRMovementType;
  readonly gainSoFar: Balance;
  readonly value: Balance;
  readonly blockNumber: number;
  readonly timestamp: number;
  readonly txHash: string;
}

export interface Collateral<T extends CollateralAssetType | string>
  extends Balance {
  readonly asset: T;
}

export interface MakerDAOVault
  extends CollateralizedLoan<Collateral<CollateralAssetType>> {
  readonly collateralType: string;
  readonly collateralizationRatio?: string;
  readonly stabilityFee: string;
  readonly liquidationRatio: string;
  readonly liquidationPrice: BigNumber;
}

export interface MakerDAOVaultDetails {
  readonly identifier: string;
  readonly creationTs: number;
  readonly totalInterestOwed: BigNumber;
  readonly totalLiquidated: Balance;
  readonly events: MakerDAOVaultEvent[];
}

interface MakerDAOVaultEvent {
  readonly eventType: MakerDAOVaultEventType;
  readonly value: Balance;
  readonly timestamp: number;
  readonly txHash: string;
}

export type MakerDAOVaultModel =
  | MakerDAOVault
  | (MakerDAOVault & MakerDAOVaultDetails);

export interface LoanSummary {
  readonly totalCollateralUsd: BigNumber;
  readonly totalDebt: BigNumber;
}

export interface CollateralizedLoan<
  C extends
    | Collateral<CollateralAssetType | string>
    | Collateral<CollateralAssetType | string>[]
> extends DefiLoan {
  readonly collateral: C;
  readonly debt: Balance;
}

export interface AaveLoan
  extends AaveBorrowingRates,
    CollateralizedLoan<Collateral<string>[]> {
  readonly events: AaveHistoryEvents[];
  readonly totalLost: AaveHistoryTotal;
  readonly liquidationEarned: AaveHistoryTotal;
}

export interface DefiBalance extends BaseDefiBalance {
  readonly address: string;
  readonly protocol: SupportedDefiProtocols;
}

export interface BaseDefiBalance extends HasBalance {
  readonly effectiveInterestRate: string;
  readonly asset: string;
}

interface MakerDAOLendingHistoryExtras {
  gainSoFar: Balance;
}

interface HistoryExtras<T> {
  readonly eventType: T;
  readonly asset: string;
  readonly value: Balance;
  readonly toAsset?: string;
  readonly toValue: Balance;
  readonly realizedPnl?: Balance;
}

interface LendingHistoryExtras {
  readonly aave: {};
  readonly makerdao: MakerDAOLendingHistoryExtras;
  readonly compound: HistoryExtras<CompoundEventType>;
  readonly yearn_vaults: HistoryExtras<YearnEventType>;
  readonly yearn_vaults_v2: HistoryExtras<YearnEventType>;
  readonly uniswap: {};
}

export interface DefiLendingHistory<T extends SupportedDefiProtocols> {
  id: string;
  eventType: EventType;
  protocol: T;
  address: string;
  asset: string;
  atoken?: string;
  value: Balance;
  extras: LendingHistoryExtras[T];
  blockNumber: number;
  timestamp: number;
  txHash: string;
}

export interface DefiLoan {
  readonly identifier: string;
  readonly protocol: SupportedDefiProtocols;
  readonly asset?: string;
  readonly owner?: string;
}

interface DefiProtocolInfo {
  readonly name: OverviewDefiProtocol;
}

interface DefiProtocolInfoWithIcon extends DefiProtocolInfo {
  readonly icon: string;
}

export interface TokenInfo {
  readonly tokenName: string;
  readonly tokenSymbol: string;
}

export interface DefiProtocolSummary {
  readonly protocol: DefiProtocolInfoWithIcon;
  readonly balanceUsd?: BigNumber;
  readonly assets: DefiAsset[];
  readonly tokenInfo: TokenInfo | null;
  readonly depositsUrl?: string;
  readonly liabilitiesUrl?: string;
  readonly totalCollateralUsd: BigNumber;
  readonly totalDebtUsd: BigNumber;
  readonly totalLendingDepositUsd: BigNumber;
}

export interface DefiAsset extends HasBalance {
  readonly tokenAddress: string;
  readonly tokenName: string;
  readonly tokenSymbol: string;
}

interface DefiProtocolData {
  readonly protocol: DefiProtocolInfo;
  readonly balanceType: DefiBalanceType;
  readonly baseBalance: DefiAsset;
  readonly underlyingBalances: DefiAsset[];
}

export interface AllDefiProtocols {
  readonly [asset: string]: DefiProtocolData[];
}

export interface ProfitLossModel {
  readonly address: string;
  readonly asset: string;
  readonly value: Balance;
}

export interface UniswapBalance {
  readonly account: string;
  readonly assets: UniswapAsset[];
  readonly poolAddress: string;
  readonly totalSupply: BigNumber | null;
  readonly userBalance: Balance;
}

type UniswapEventType = typeof UNISWAP_EVENT_TYPE[number];

interface DexSwap {
  readonly amount0In: BigNumber;
  readonly amount0Out: BigNumber;
  readonly amount1In: BigNumber;
  readonly amount1Out: BigNumber;
  readonly fromAddress: string;
  readonly location: 'uniswap';
  readonly logIndex: number;
  readonly toAddress: string;
  readonly token0: string;
  readonly token1: string;
  readonly txHash: string;
}

export interface DexTrade {
  readonly address: string;
  readonly amount: BigNumber;
  readonly baseAsset: string;
  readonly fee: BigNumber;
  readonly feeCurrency: string;
  readonly location: 'uniswap' | 'balancer';
  readonly quoteAsset: string;
  readonly rate: BigNumber;
  readonly swaps: DexSwap[];
  readonly timestamp: number;
  readonly tradeId: string;
  readonly tradeType: TradeType;
  readonly txHash: string;
}

export interface DexTrades {
  readonly [address: string]: DexTrade[];
}

interface UniswapEvent {
  readonly amount0: BigNumber;
  readonly amount1: BigNumber;
  readonly eventType: UniswapEventType;
  readonly logIndex: number;
  readonly lpAmount: BigNumber;
  readonly timestamp: number;
  readonly txHash: string;
  readonly usdPrice: BigNumber;
}

interface UniswapPoolDetails {
  readonly address: string;
  readonly events: UniswapEvent[];
  readonly poolAddress: string;
  readonly profitLoss0: BigNumber;
  readonly profitLoss1: BigNumber;
  readonly token0: string;
  readonly token1: string;
  readonly usdProfitLoss: BigNumber;
}

export interface UniswapPool {
  readonly address: string;
  readonly assets: string[];
}

export interface UniswapEvents {
  readonly [address: string]: UniswapPoolDetails[];
}

export interface UniswapPoolProfit
  extends Omit<UniswapPoolDetails, 'events' | 'address'> {}

export interface UniswapEventDetails
  extends UniswapEvent,
    Pick<UniswapPoolDetails, 'address' | 'poolAddress' | 'token0' | 'token1'> {}

export interface BalancerUnderlyingToken {
  readonly token: string;
  readonly totalAmount: BigNumber;
  readonly userBalance: Balance;
  readonly usdPrice: BigNumber;
  readonly weight: string;
}

interface BalancerBalance {
  readonly address: string;
  readonly tokens: BalancerUnderlyingToken[];
  readonly totalAmount: BigNumber;
  readonly userBalance: Balance;
}

export interface BalancerBalanceWithOwner extends BalancerBalance {
  readonly owner: string;
}

export interface BalancerBalances {
  readonly [address: string]: BalancerBalance[];
}

interface PoolToken {
  readonly token: string;
  readonly weight: string;
}

export interface PoolAmounts {
  readonly [asset: string]: BigNumber;
}

export type Pool = {
  readonly name: string;
  readonly address: string;
};

export interface BalancerEvent {
  readonly txHash: string;
  readonly logIndex: number;
  readonly timestamp: number;
  readonly eventType: EventType;
  readonly lpBalance: Balance;
  readonly amounts: PoolAmounts;
  readonly pool?: Pool;
}

interface BalancerPoolDetails {
  readonly poolAddress: string;
  readonly poolTokens: PoolToken[];
  readonly events: BalancerEvent[];
  readonly profitLossAmounts: PoolAmounts;
  readonly usdProfitLoss: BigNumber;
}

export interface BalancerEvents {
  readonly [address: string]: BalancerPoolDetails[];
}

export interface BalancerProfitLoss {
  readonly pool: Pool;
  readonly tokens: string[];
  readonly usdProfitLoss: BigNumber;
  readonly profitLossAmount: PoolAmounts;
}
