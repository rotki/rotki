import { Balance, BigNumber } from '@rotki/common';
import { HasBalance } from '@rotki/common/lib';
import { DefiProtocol } from '@rotki/common/lib/blockchain';
import {
  AaveBorrowingRates,
  AaveHistoryEvents,
  AaveHistoryTotal
} from '@rotki/common/lib/defi/aave';
import { DexTrade } from '@rotki/common/lib/defi/dex';
import {
  CollateralAssetType,
  DefiBalanceType,
  DSRMovementType,
  EventType,
  MakerDAOVaultEventType
} from '@/services/defi/types';
import { CompoundEventType } from '@/services/defi/types/compound';
import { YearnEventType } from '@/services/defi/types/yearn';
import { AIRDROP_POAP, AIRDROPS, OVERVIEW_PROTOCOLS } from '@/store/defi/const';

export type OverviewDefiProtocol = typeof OVERVIEW_PROTOCOLS[number];

export interface DefiState {
  allProtocols: AllDefiProtocols;
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

export interface MakerDAOVaultEvent {
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
  readonly protocol: DefiProtocol;
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

type LendingHistoryExtras = {
  readonly [DefiProtocol.AAVE]: {};
  readonly [DefiProtocol.MAKERDAO_VAULTS]: {};
  readonly [DefiProtocol.MAKERDAO_DSR]: MakerDAOLendingHistoryExtras;
  readonly [DefiProtocol.COMPOUND]: HistoryExtras<CompoundEventType>;
  readonly [DefiProtocol.YEARN_VAULTS]: HistoryExtras<YearnEventType>;
  readonly [DefiProtocol.YEARN_VAULTS_V2]: HistoryExtras<YearnEventType>;
  readonly [DefiProtocol.UNISWAP]: {};
  readonly [DefiProtocol.LIQUITY]: {};
};

export interface DefiLendingHistory<T extends DefiProtocol> {
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
  readonly protocol: DefiProtocol;
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
  readonly deposits: boolean;
  readonly liabilities: boolean;
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

export interface DexTrades {
  readonly [address: string]: DexTrade[];
}
