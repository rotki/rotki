import { NumericString } from '@rotki/common';
import { z } from 'zod/v4';
import { BalanceType } from '@/types/balances';

export const BalanceSnapshot = z.object({
  amount: NumericString,
  assetIdentifier: z.string(),
  category: z.enum(BalanceType),
  timestamp: z.number(),
  usdValue: NumericString,
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
  location: z.string(),
  timestamp: z.number(),
  usdValue: NumericString,
});

export type LocationDataSnapshot = z.infer<typeof LocationDataSnapshot>;

export interface LocationDataSnapshotPayload {
  timestamp: number;
  location: string;
  usdValue: string;
}

export const Snapshot = z.object({
  balancesSnapshot: z.array(BalanceSnapshot),
  locationDataSnapshot: z.array(LocationDataSnapshot),
});

export type Snapshot = z.infer<typeof Snapshot>;

export interface SnapshotPayload {
  balancesSnapshot: BalanceSnapshotPayload[];
  locationDataSnapshot: LocationDataSnapshotPayload[];
}
