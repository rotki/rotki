import { default as BigNumber } from 'bignumber.js';
import { Balance } from '@/model/blockchain-balances';
import {
  AaveEventType,
  CollateralAssetType,
  DefiBalanceType,
  DSRMovementType,
  MakerDAOVaultEventType,
  SupportedDefiProtocols
} from '@/services/defi/types';
import { Status } from '@/store/defi/status';

export interface DefiState {
  status: Status;
  lendingHistoryStatus: Status;
  borrowingHistoryStatus: Status;
  dsrHistory: DSRHistory;
  dsrBalances: DSRBalances;
  makerDAOVaults: MakerDAOVault[];
  makerDAOVaultDetails: MakerDAOVaultDetails[];
  aaveBalances: AaveBalances;
  aaveHistory: AaveHistory;
  allProtocols: AllDefiProtocols;
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
  readonly gainSoFar: BigNumber;
  readonly gainSoFarUsdValue: BigNumber;
  readonly movements: DSRMovement[];
}

export interface DSRHistory {
  readonly [address: string]: DSRHistoryItem;
}

export interface DSRMovement {
  readonly movementType: DSRMovementType;
  readonly gainSoFar: Balance;
  readonly balance: Balance;
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
  readonly amount: BigNumber;
  readonly amountUsdValue: BigNumber;
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

export interface BaseDefiAsset {
  readonly balance: Balance;
}

export interface AaveBorrowingRates {
  readonly stableApr: string;
  readonly variableApr: string;
}

export interface AaveBorrowingAsset extends BaseDefiAsset, AaveBorrowingRates {}

export interface CollateralizedLoan<T extends CollateralAssetType | string>
  extends DefiLoan {
  readonly owner: string;
  readonly collateral: Collateral<T>;
  readonly debt: Balance;
}

export interface AaveLoan
  extends AaveBorrowingRates,
    CollateralizedLoan<string> {
  readonly owner: string;
}

export interface AaveLendingAsset extends BaseDefiAsset {
  readonly apy: string;
}

export interface AaveBorrowing {
  readonly [asset: string]: AaveBorrowingAsset;
}

export interface AaveLending {
  readonly [asset: string]: AaveLendingAsset;
}

interface AaveBalance {
  readonly lending: AaveLending;
  readonly borrowing: AaveBorrowing;
}

export interface AaveBalances {
  readonly [address: string]: AaveBalance;
}

export interface AaveHistoryEvents {
  eventType: AaveEventType;
  asset: string;
  value: Balance;
  blockNumber: number;
  timestamp: number;
  txHash: string;
}

export interface AaveHistoryTotalEarned {
  readonly [asset: string]: Balance;
}

export interface AaveAccountHistory {
  readonly events: AaveHistoryEvents[];
  readonly totalEarned: AaveHistoryTotalEarned;
}

export interface AaveHistory {
  readonly [address: string]: AaveAccountHistory;
}

export interface DefiBalance extends BaseDefiAsset {
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

export interface DefiAsset extends BaseDefiAsset {
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
