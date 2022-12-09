import { Balance, type BigNumber } from '@rotki/common';
import { z } from 'zod';

export interface Eth2Validator {
  readonly validatorIndex?: string;
  readonly publicKey?: string;
  readonly ownershipPercentage?: string;
}

export interface LocationBalance {
  readonly location: string;
  readonly usdValue: BigNumber;
}

export type BalanceByLocation = Record<string, BigNumber>;

export const AssetBalances = z.record(Balance);

export type AssetBalances = z.infer<typeof AssetBalances>;

export const AccountAssetBalances = z.record(AssetBalances);

export type AccountAssetBalances = z.infer<typeof AccountAssetBalances>;
