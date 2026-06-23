import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { BalanceType } from '@/modules/balances/types/balances';
import { type BalanceSnapshot, BalanceSnapshotSchema, type LocationDataSnapshot, LocationDataSnapshotSchema, type Snapshot } from '@/modules/dashboard/snapshots';
import { applyBalanceBulkDelete, applyReconcileLocations, rebuildSnapshotAfterBalanceChange } from '@/modules/dashboard/snapshots/utils/snapshot-mutations';
import { getTotalValue } from '@/modules/dashboard/snapshots/utils/snapshot-totals';

function balance(usdValue: string, category: BalanceType = BalanceType.ASSET): BalanceSnapshot {
  return BalanceSnapshotSchema.parse({ amount: '1', assetIdentifier: 'ETH', category, timestamp: 1700000000, usdValue });
}

function location(loc: string, usdValue: string): LocationDataSnapshot {
  return LocationDataSnapshotSchema.parse({ location: loc, timestamp: 1700000000, usdValue });
}

function snapshot(balances: BalanceSnapshot[], locations: LocationDataSnapshot[]): Snapshot {
  return { balancesSnapshot: balances, locationDataSnapshot: locations };
}

describe('modules/dashboard/snapshots/utils/snapshot-mutations', () => {
  it('should update the affected location subtotal and recompute the total', () => {
    const snap = snapshot(
      [balance('100')],
      [location('kraken', '40'), location('total', '40')],
    );
    const result = rebuildSnapshotAfterBalanceChange({
      balancesSnapshot: [balance('100'), balance('70')],
      location: 'kraken',
      locationBalance: { after: bigNumberify(110), before: bigNumberify(40) },
      snapshot: snap,
      timestamp: 1700000000,
    });

    expect(result.locationDataSnapshot.find(i => i.location === 'kraken')?.usdValue.toNumber()).toBe(110);
    // total recomputed from net balances 100 + 70
    expect(result.locationDataSnapshot.find(i => i.location === 'total')?.usdValue.toNumber()).toBe(170);
  });

  it('should append a new location row when the location does not exist', () => {
    const snap = snapshot([balance('100')], [location('total', '100')]);
    const result = rebuildSnapshotAfterBalanceChange({
      balancesSnapshot: [balance('100'), balance('50')],
      location: 'binance',
      locationBalance: { after: bigNumberify(50), before: bigNumberify(0) },
      snapshot: snap,
      timestamp: 1700000000,
    });

    expect(result.locationDataSnapshot.find(i => i.location === 'binance')?.usdValue.toNumber()).toBe(50);
    expect(result.locationDataSnapshot.find(i => i.location === 'total')?.usdValue.toNumber()).toBe(150);
  });

  it('should net liabilities into the recomputed total', () => {
    const snap = snapshot([], [location('total', '0')]);
    const result = rebuildSnapshotAfterBalanceChange({
      balancesSnapshot: [balance('100'), balance('30', BalanceType.LIABILITY)],
      location: '',
      locationBalance: null,
      snapshot: snap,
      timestamp: 1700000000,
    });

    expect(result.locationDataSnapshot.find(i => i.location === 'total')?.usdValue.toNumber()).toBe(70);
  });

  it('should skip the location update when location is empty', () => {
    const snap = snapshot([balance('100')], [location('kraken', '40'), location('total', '40')]);
    const result = rebuildSnapshotAfterBalanceChange({
      balancesSnapshot: [balance('100')],
      location: '',
      locationBalance: null,
      snapshot: snap,
      timestamp: 1700000000,
    });

    expect(result.locationDataSnapshot.find(i => i.location === 'kraken')?.usdValue.toNumber()).toBe(40);
    expect(result.locationDataSnapshot.find(i => i.location === 'total')?.usdValue.toNumber()).toBe(100);
  });

  it('should not throw when there is no total row', () => {
    const snap = snapshot([balance('100')], [location('kraken', '40')]);
    expect(() => rebuildSnapshotAfterBalanceChange({
      balancesSnapshot: [balance('100')],
      location: '',
      locationBalance: null,
      snapshot: snap,
      timestamp: 1700000000,
    })).not.toThrow();
  });

  describe('applyBalanceBulkDelete', () => {
    function named(assetIdentifier: string, usdValue: string): BalanceSnapshot {
      return BalanceSnapshotSchema.parse({ amount: '1', assetIdentifier, category: BalanceType.ASSET, timestamp: 1700000000, usdValue });
    }

    function withZeroValues(): Snapshot {
      return snapshot(
        [named('BTC', '100'), named('SPAM', '0'), named('ETH', '50'), named('JUNK', '0')],
        [location('kraken', '100'), location('ledger', '50'), location('total', '150')],
      );
    }

    it('should remove every listed index in one pass', () => {
      const result = applyBalanceBulkDelete(withZeroValues(), [1, 3]);
      expect(result.balancesSnapshot.map(item => item.assetIdentifier)).toEqual(['BTC', 'ETH']);
    });

    it('should not touch location subtotals when sweeping valueless rows', () => {
      const result = applyBalanceBulkDelete(withZeroValues(), [1, 3]);
      expect(result.locationDataSnapshot.find(item => item.location === 'kraken')?.usdValue.toNumber()).toBe(100);
      expect(result.locationDataSnapshot.find(item => item.location === 'ledger')?.usdValue.toNumber()).toBe(50);
    });

    it('should leave the total unchanged when the removed rows have no value', () => {
      const result = applyBalanceBulkDelete(withZeroValues(), [1, 3]);
      expect(getTotalValue(result.locationDataSnapshot).toNumber()).toBe(150);
    });

    it('should return the snapshot untouched for an empty index list', () => {
      const original = withZeroValues();
      expect(applyBalanceBulkDelete(original, [])).toBe(original);
    });

    it('should not mutate the original balances', () => {
      const original = withZeroValues();
      applyBalanceBulkDelete(original, [1, 3]);
      expect(original.balancesSnapshot).toHaveLength(4);
    });
  });

  describe('applyReconcileLocations', () => {
    it('should absorb the difference into the chosen location and snap the total to balances', () => {
      // balances 100; locations 60 + 20 = 80; stored total 80 — all off.
      const snap = snapshot(
        [balance('100')],
        [location('kraken', '60'), location('ledger', '20'), location('total', '80')],
      );
      const result = applyReconcileLocations(snap, 'kraken', bigNumberify('100'));
      expect(result.locationDataSnapshot.find(i => i.location === 'kraken')?.usdValue.toNumber()).toBe(80); // 60 + (100 - 80)
      expect(result.locationDataSnapshot.find(i => i.location === 'ledger')?.usdValue.toNumber()).toBe(20);
      // Total snaps to the balances sum, never the locations sum.
      expect(getTotalValue(result.locationDataSnapshot).toNumber()).toBe(100);
    });

    it('should create the absorbing location when missing and target the balances sum', () => {
      const snap = snapshot([balance('100')], [location('kraken', '80'), location('total', '80')]);
      const result = applyReconcileLocations(snap, 'ledger', bigNumberify('100'));
      expect(result.locationDataSnapshot.find(i => i.location === 'ledger')?.usdValue.toNumber()).toBe(20); // 0 + 20
      expect(getTotalValue(result.locationDataSnapshot).toNumber()).toBe(100);
    });
  });
});
