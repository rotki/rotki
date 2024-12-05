import { z } from 'zod';
import { AssetBalance, Balance } from '../balances';
import { NumericString } from '../numbers';

const TimedEntry = z.object({ time: z.number().positive() });

const TimedBalance = Balance.merge(TimedEntry);

export type TimedBalance = z.infer<typeof TimedBalance>;

export const TimedBalances = z.array(TimedBalance);

export type TimedBalances = z.infer<typeof TimedBalances>;

export const OwnedAssets = z.array(z.string());

export type OwnedAssets = z.infer<typeof OwnedAssets>;

const LocationDataItem = z.object({
  location: z.string().min(1),
  time: z.number().positive(),
  usdValue: NumericString,
});

export const LocationData = z.array(LocationDataItem);

export type LocationData = z.infer<typeof LocationData>;

const TimedAssetBalance = AssetBalance.merge(TimedEntry);

export const TimedAssetBalances = z.array(TimedAssetBalance);

export type TimedAssetBalances = z.infer<typeof TimedAssetBalances>;

export const NetValue = z.object({
  data: z.array(NumericString),
  times: z.array(z.number()),
});

export type NetValue = z.infer<typeof NetValue>;
