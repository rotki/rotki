import { default as BigNumber } from 'bignumber.js';
import {
  AaveEventType,
  CollateralAssetType,
  DefiBalanceType,
  DSRMovementType,
  MakerDAOVaultEventType,
  SupportedDefiProtocols
} from '@/services/defi/types';
import {
  AaveBalances,
  AaveBorrowingRates,
  AaveHistory
} from '@/services/defi/types/aave';
import {
  CompoundBalances,
  CompoundHistory
} from '@/services/defi/types/compound';
import { Balance, HasBalance } from '@/services/types-api';

export interface DefiState {
  dsrHistory: DSRHistory;
  dsrBalances: DSRBalances;
  makerDAOVaults: MakerDAOVault[];
  makerDAOVaultDetails: MakerDAOVaultDetails[];
  aaveBalances: AaveBalances;
  aaveHistory: AaveHistory;
  allProtocols: AllDefiProtocols;
  compoundBalances: CompoundBalances;
  compoundHistory: CompoundHistory;
}

export interface DSRBalances {
  readonly currentDSR: BigNumber;
  readonly balances: {
    [account: string]: {
      amount: BigNumber;
      usdValue: BigNumber;
    };
  };
}

export interface DSRHistoryItem {
  readonly gainSoFar: Balance;
  readonly movements: DSRMovement[];
}

export interface DSRHistory {
  readonly [address: string]: DSRHistoryItem;
}

export interface DSRMovement {
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

export interface MakerDAOVault extends CollateralizedLoan<CollateralAssetType> {
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

export interface CollateralizedLoan<T extends CollateralAssetType | string>
  extends DefiLoan {
  readonly collateral: Collateral<T>;
  readonly debt: Balance;
}

export interface AaveLoan
  extends AaveBorrowingRates,
    CollateralizedLoan<string> {}

export interface CompoundLoan extends CollateralizedLoan<string> {
  readonly apr: string;
}

export interface DefiBalance extends HasBalance {
  readonly address: string;
  readonly asset: string;
  readonly protocol: SupportedDefiProtocols;
  readonly effectiveInterestRate: string;
}

interface MakerDAOLendingHistoryExtras {
  gainSoFar: Balance;
}

export interface LendingHistoryExtras {
  readonly aave: {};
  readonly makerdao: MakerDAOLendingHistoryExtras;
  readonly compound: {};
}

export interface DefiLendingHistory<T extends SupportedDefiProtocols> {
  id: number;
  eventType: AaveEventType | DSRMovementType;
  protocol: T;
  address: string;
  asset: string;
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

export interface DefiProtocolInfo {
  readonly name: string;
  readonly icon: string;
}

export interface TokenInfo {
  readonly tokenName: string;
  readonly tokenSymbol: string;
}

export interface DefiProtocolSummary {
  readonly protocol: DefiProtocolInfo;
  readonly balanceUsd?: BigNumber;
  readonly assets: DefiAsset[];
  readonly tokenInfo?: TokenInfo;
  readonly lendingUrl?: string;
  readonly borrowingUrl?: string;
  readonly totalCollateralUsd: BigNumber;
  readonly totalDebtUsd: BigNumber;
  readonly totalLendingDepositUsd: BigNumber;
}

export interface DefiAsset extends HasBalance {
  readonly tokenAddress: string;
  readonly tokenName: string;
  readonly tokenSymbol: string;
}

export interface DefiProtocolData {
  readonly protocol: DefiProtocolInfo;
  readonly balanceType: DefiBalanceType;
  readonly baseBalance: DefiAsset;
  readonly underlyingBalances: DefiAsset[];
}

export interface AllDefiProtocols {
  readonly [asset: string]: DefiProtocolData[];
}
