import { Balance } from '@rotki/common';
import { z } from 'zod';
import { ProtocolVersion } from '@/types/defi/index';

export const WITHDRAW = 'withdraw';
export const DEPOSIT = 'deposit';
export const YEARN_EVENTS = [WITHDRAW, DEPOSIT] as const;

const YearnEventType = z.enum(YEARN_EVENTS);

export type YearnEventType = z.infer<typeof YearnEventType>;

const YearnVaultEvent = z.object({
  eventType: YearnEventType,
  blockNumber: z.number(),
  timestamp: z.number(),
  fromAsset: z.string(),
  fromValue: Balance,
  toAsset: z.string(),
  toValue: Balance,
  realizedPnl: Balance.nullable(),
  txHash: z.string(),
  logIndex: z.number()
});

const YearnVault = z.object({
  events: z.array(YearnVaultEvent),
  profitLoss: Balance
});

const AccountYearnVault = z.record(YearnVault);

export const YearnVaultsHistory = z.record(AccountYearnVault);

export type YearnVaultsHistory = z.infer<typeof YearnVaultsHistory>;

export interface YearnVaultProfitLoss {
  readonly value: Balance;
  readonly asset: string;
  readonly vault: string;
}

const YearnVaultBalance = z.object({
  underlyingToken: z.string(),
  vaultToken: z.string(),
  underlyingValue: Balance,
  vaultValue: Balance,
  roi: z.string()
});

export type YearnVaultBalance = z.infer<typeof YearnVaultBalance>;

const YearnVaultAsset = z
  .object({
    vault: z.string(),
    version: z.nativeEnum(ProtocolVersion)
  })
  .merge(YearnVaultBalance);

export type YearnVaultAsset = z.infer<typeof YearnVaultAsset>;

const AccountYearnVaultEntry = z.record(YearnVaultBalance);

export const YearnVaultsBalances = z.record(AccountYearnVaultEntry);

export type YearnVaultsBalances = z.infer<typeof YearnVaultsBalances>;
