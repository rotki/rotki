import { Balance } from '@rotki/common';
import { z } from 'zod';
import { ProtocolVersion } from '@/types/defi/index';

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
  roi: z.string().optional(),
});

export type YearnVaultBalance = z.infer<typeof YearnVaultBalance>;

const YearnVaultAsset = z
  .object({
    vault: z.string(),
    version: z.nativeEnum(ProtocolVersion),
  })
  .merge(YearnVaultBalance);

export type YearnVaultAsset = z.infer<typeof YearnVaultAsset>;

const AccountYearnVaultEntry = z.record(YearnVaultBalance);

export const YearnVaultsBalances = z.record(AccountYearnVaultEntry);

export type YearnVaultsBalances = z.infer<typeof YearnVaultsBalances>;
