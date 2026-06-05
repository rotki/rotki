import type { BalanceSnapshot as BalanceSnapshotType, LocationDataSnapshot as LocationDataSnapshotType, Snapshot } from '@/modules/dashboard/snapshots';
import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { BalanceType } from '@/modules/balances/types/balances';
import { BalanceSnapshot, LocationDataSnapshot } from '@/modules/dashboard/snapshots';
import {
  locationBalanceAfterDelete,
  locationBalanceAfterEdit,
} from '@/modules/dashboard/snapshots/lib/snapshot-location-balance';

interface BalanceOptions {
  usdValue: string;
  category?: BalanceType;
  assetIdentifier?: string;
  amount?: string;
}

function balance(options: BalanceOptions): BalanceSnapshotType {
  return BalanceSnapshot.parse({
    amount: options.amount ?? '1',
    assetIdentifier: options.assetIdentifier ?? 'ETH',
    category: options.category ?? BalanceType.ASSET,
    timestamp: 1700000000,
    usdValue: options.usdValue,
  });
}

function location(loc: string, usdValue: string): LocationDataSnapshotType {
  return LocationDataSnapshot.parse({ location: loc, timestamp: 1700000000, usdValue });
}

function snapshot(balances: BalanceSnapshotType[], locations: LocationDataSnapshotType[]): Snapshot {
  return { balancesSnapshot: balances, locationDataSnapshot: locations };
}

describe('modules/dashboard/snapshots/lib/snapshot-location-balance', () => {
  describe('locationBalanceAfterEdit', () => {
    it('should add a new asset to the existing subtotal', () => {
      const snap = snapshot([], [location('kraken', '100')]);
      const result = locationBalanceAfterEdit({
        category: BalanceType.ASSET,
        editIndex: null,
        location: 'kraken',
        snapshot: snap,
        usdValue: bigNumberify(40),
      });
      expect(result.before.toNumber()).toBe(100);
      expect(result.after.toNumber()).toBe(140);
    });

    it('should subtract a new liability from the subtotal', () => {
      const snap = snapshot([], [location('kraken', '100')]);
      const result = locationBalanceAfterEdit({
        category: BalanceType.LIABILITY,
        editIndex: null,
        location: 'kraken',
        snapshot: snap,
        usdValue: bigNumberify(40),
      });
      expect(result.after.toNumber()).toBe(60);
    });

    it('should start from zero when the location has no row yet', () => {
      const snap = snapshot([], [location('kraken', '100')]);
      const result = locationBalanceAfterEdit({
        category: BalanceType.ASSET,
        editIndex: null,
        location: 'binance',
        snapshot: snap,
        usdValue: bigNumberify(40),
      });
      expect(result.before.toNumber()).toBe(0);
      expect(result.after.toNumber()).toBe(40);
    });

    it('should remove the previous balance then add the edited one', () => {
      // existing asset of 40 in kraken, edited up to 70
      const snap = snapshot(
        [balance({ category: BalanceType.ASSET, usdValue: '40' })],
        [location('kraken', '100')],
      );
      const result = locationBalanceAfterEdit({
        category: BalanceType.ASSET,
        editIndex: 0,
        location: 'kraken',
        snapshot: snap,
        usdValue: bigNumberify(70),
      });
      // 100 - 40 (old) + 70 (new) = 130
      expect(result.after.toNumber()).toBe(130);
    });

    it('should handle editing an asset into a liability', () => {
      const snap = snapshot(
        [balance({ category: BalanceType.ASSET, usdValue: '40' })],
        [location('kraken', '100')],
      );
      const result = locationBalanceAfterEdit({
        category: BalanceType.LIABILITY,
        editIndex: 0,
        location: 'kraken',
        snapshot: snap,
        usdValue: bigNumberify(40),
      });
      // 100 - 40 (old asset) - 40 (new liability) = 20
      expect(result.after.toNumber()).toBe(20);
    });
  });

  describe('locationBalanceAfterDelete', () => {
    it('should remove a deleted asset from the subtotal', () => {
      const snap = snapshot(
        [balance({ category: BalanceType.ASSET, usdValue: '40' })],
        [location('kraken', '100')],
      );
      const result = locationBalanceAfterDelete({ index: 0, location: 'kraken', snapshot: snap });
      expect(result?.before.toNumber()).toBe(100);
      expect(result?.after.toNumber()).toBe(60);
    });

    it('should add a deleted liability back to the subtotal', () => {
      const snap = snapshot(
        [balance({ category: BalanceType.LIABILITY, usdValue: '40' })],
        [location('kraken', '100')],
      );
      const result = locationBalanceAfterDelete({ index: 0, location: 'kraken', snapshot: snap });
      expect(result?.after.toNumber()).toBe(140);
    });

    it('should return null when the location row is missing', () => {
      const snap = snapshot([balance({ usdValue: '40' })], [location('kraken', '100')]);
      expect(locationBalanceAfterDelete({ index: 0, location: 'binance', snapshot: snap })).toBeNull();
    });

    it('should return null when the balance is missing', () => {
      const snap = snapshot([], [location('kraken', '100')]);
      expect(locationBalanceAfterDelete({ index: 5, location: 'kraken', snapshot: snap })).toBeNull();
    });
  });
});
