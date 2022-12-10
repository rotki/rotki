import { Balance, type BigNumber, NumericString } from '@rotki/common';
import { z } from 'zod';
import { type Collateral, type CollateralizedLoan } from '@/types/defi/index';

const DSRMovementType = z.enum(['withdrawal', 'deposit'] as const);

export type DSRMovementType = z.infer<typeof DSRMovementType>;

const MakerDAOVaultEventType = z.enum([
  'deposit',
  'withdraw',
  'generate',
  'payback',
  'liquidation'
] as const);

export const ApiMakerDAOVault = z.object({
  identifier: z.number(),
  collateralType: z.string(),
  owner: z.string(),
  collateralAsset: z.string(),
  collateral: Balance,
  debt: Balance,
  collateralizationRatio: z.string().nullable(),
  liquidationRatio: z.string(),
  liquidationPrice: NumericString.nullable(),
  stabilityFee: z.string()
});

export type ApiMakerDAOVault = z.infer<typeof ApiMakerDAOVault>;

export const ApiMakerDAOVaults = z.array(ApiMakerDAOVault);

export type ApiMakerDAOVaults = z.infer<typeof ApiMakerDAOVaults>;

export const DSRBalances = z.object({
  currentDsr: NumericString,
  balances: z.record(Balance)
});

export type DSRBalances = z.infer<typeof DSRBalances>;

const DSRMovement = z.object({
  movementType: DSRMovementType,
  gainSoFar: Balance,
  value: Balance,
  blockNumber: z.number(),
  timestamp: z.number(),
  txHash: z.string()
});

const DSRHistoryItem = z.object({
  gainSoFar: Balance,
  movements: z.array(DSRMovement)
});

export const DSRHistory = z.record(DSRHistoryItem);

export type DSRHistory = z.infer<typeof DSRHistory>;

export interface MakerDAOVault extends CollateralizedLoan<Collateral> {
  readonly collateralType: string;
  readonly collateralizationRatio?: string;
  readonly stabilityFee: string;
  readonly liquidationRatio: string;
  readonly liquidationPrice: BigNumber;
}

const MakerDAOVaultEvent = z.object({
  eventType: MakerDAOVaultEventType,
  value: Balance,
  timestamp: z.number(),
  txHash: z.string()
});

export type MakerDAOVaultEvent = z.infer<typeof MakerDAOVaultEvent>;

const MakerDAOVaultDetail = z.object({
  identifier: z.number().transform(arg => arg.toString()),
  creationTs: z.number(),
  totalInterestOwed: NumericString,
  totalLiquidated: Balance,
  events: z.array(MakerDAOVaultEvent)
});
export type MakerDAOVaultDetail = z.infer<typeof MakerDAOVaultDetail>;

export const MakerDAOVaultDetails = z.array(MakerDAOVaultDetail);
export type MakerDAOVaultDetails = z.infer<typeof MakerDAOVaultDetails>;

export type MakerDAOVaultModel =
  | MakerDAOVault
  | (MakerDAOVault & MakerDAOVaultDetail);

export interface MakerDAOLendingHistoryExtras {
  gainSoFar: Balance;
}
