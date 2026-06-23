import { NumericString } from '@rotki/common';
import { z } from 'zod/v4';
import { BalanceType } from '@/modules/balances/types/balances';

export const BalanceSnapshotSchema = z.object({
  amount: NumericString,
  assetIdentifier: z.string(),
  category: z.enum(BalanceType),
  timestamp: z.number(),
  usdValue: NumericString,
});

export type BalanceSnapshot = z.infer<typeof BalanceSnapshotSchema>;

export interface BalanceSnapshotPayload {
  timestamp: number;
  category: BalanceType;
  assetIdentifier: string;
  amount: string;
  usdValue: string;
}

export const LocationDataSnapshotSchema = z.object({
  location: z.string(),
  timestamp: z.number(),
  usdValue: NumericString,
});

export type LocationDataSnapshot = z.infer<typeof LocationDataSnapshotSchema>;

export interface LocationDataSnapshotPayload {
  timestamp: number;
  location: string;
  usdValue: string;
}

export const SnapshotSchema = z.object({
  balancesSnapshot: z.array(BalanceSnapshotSchema),
  locationDataSnapshot: z.array(LocationDataSnapshotSchema),
});

export type Snapshot = z.infer<typeof SnapshotSchema>;

export interface SnapshotPayload {
  balancesSnapshot: BalanceSnapshotPayload[];
  locationDataSnapshot: LocationDataSnapshotPayload[];
}
