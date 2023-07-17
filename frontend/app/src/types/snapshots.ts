import { NumericString } from '@rotki/common';
import { z } from 'zod';
import { BalanceType } from '@/types/balances';

export const BalanceSnapshot = z.object({
  timestamp: z.number(),
  category: z.nativeEnum(BalanceType),
  assetIdentifier: z.string(),
  amount: NumericString,
  usdValue: NumericString
});

export type BalanceSnapshot = z.infer<typeof BalanceSnapshot>;

export interface BalanceSnapshotPayload {
  timestamp: number;
  category: BalanceType;
  assetIdentifier: string;
  amount: string;
  usdValue: string;
}

export const LocationDataSnapshot = z.object({
  timestamp: z.number(),
  location: z.string(),
  usdValue: NumericString
});

export type LocationDataSnapshot = z.infer<typeof LocationDataSnapshot>;

export interface LocationDataSnapshotPayload {
  timestamp: number;
  location: string;
  usdValue: string;
}

export const Snapshot = z.object({
  balancesSnapshot: z.array(BalanceSnapshot),
  locationDataSnapshot: z.array(LocationDataSnapshot)
});

export type Snapshot = z.infer<typeof Snapshot>;

export interface SnapshotPayload {
  balancesSnapshot: BalanceSnapshotPayload[];
  locationDataSnapshot: LocationDataSnapshotPayload[];
}
