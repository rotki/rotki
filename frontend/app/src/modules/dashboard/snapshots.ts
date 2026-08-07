import { NumericString } from '@rotki/common';
import { z } from 'zod';
import { BalanceType } from '@/modules/balances/types/balances';

export const BalanceSnapshotSchema = z.object({
  amount: NumericString,
  assetIdentifier: z.string(),
  category: z.enum(BalanceType),
  timestamp: z.number(),
  usdValue: NumericString,
});

export type BalanceSnapshot = z.infer<typeof BalanceSnapshotSchema>;

/**
 * Visibility of zero-value rows in the snapshot balances table. `ONLY` isolates
 * them and is entered from the summary's zero-value warning.
 */
export const ZeroValueFilter = {
  ALL: 'all',
  HIDE: 'hide',
  ONLY: 'only',
} as const;

export type ZeroValueFilter = typeof ZeroValueFilter[keyof typeof ZeroValueFilter];

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
