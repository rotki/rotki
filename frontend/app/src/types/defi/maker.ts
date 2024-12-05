import { Balance, type BigNumber, NumericString } from '@rotki/common';
import { z } from 'zod';
import type { Collateral, CollateralizedLoan } from '@/types/defi/index';

const DSRMovementType = z.enum(['withdrawal', 'deposit'] as const);

const MakerDAOVaultEventType = z.enum(['deposit', 'withdraw', 'generate', 'payback', 'liquidation'] as const);

export const ApiMakerDAOVault = z.object({
  collateral: Balance,
  collateralAsset: z.string(),
  collateralizationRatio: z.string().nullable(),
  collateralType: z.string(),
  debt: Balance,
  identifier: z.number(),
  liquidationPrice: NumericString.nullable(),
  liquidationRatio: z.string(),
  owner: z.string(),
  stabilityFee: z.string(),
});

export type ApiMakerDAOVault = z.infer<typeof ApiMakerDAOVault>;

export const ApiMakerDAOVaults = z.array(ApiMakerDAOVault);

export type ApiMakerDAOVaults = z.infer<typeof ApiMakerDAOVaults>;

export const DSRBalances = z.object({
  balances: z.record(Balance),
  currentDsr: NumericString,
});

export type DSRBalances = z.infer<typeof DSRBalances>;

const DSRMovement = z.object({
  blockNumber: z.number(),
  gainSoFar: Balance,
  movementType: DSRMovementType,
  timestamp: z.number(),
  txHash: z.string(),
  value: Balance,
});

const DSRHistoryItem = z.object({
  gainSoFar: Balance,
  movements: z.array(DSRMovement),
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
  timestamp: z.number(),
  txHash: z.string(),
  value: Balance,
});

const MakerDAOVaultDetail = z.object({
  creationTs: z.number(),
  events: z.array(MakerDAOVaultEvent),
  identifier: z.number().transform(arg => arg.toString()),
  totalInterestOwed: NumericString,
  totalLiquidated: Balance,
});

export type MakerDAOVaultDetail = z.infer<typeof MakerDAOVaultDetail>;

export const MakerDAOVaultDetails = z.array(MakerDAOVaultDetail);

export type MakerDAOVaultDetails = z.infer<typeof MakerDAOVaultDetails>;

export type MakerDAOVaultModel = MakerDAOVault | (MakerDAOVault & MakerDAOVaultDetail);
