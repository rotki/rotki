import { Balance } from '@rotki/common';
import { z } from 'zod';
import { ProtocolVersion } from '@/types/defi/index';

const YearnVaultBalance = z.object({
  roi: z.string().optional(),
  underlyingToken: z.string(),
  underlyingValue: Balance,
  vaultToken: z.string(),
  vaultValue: Balance,
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
