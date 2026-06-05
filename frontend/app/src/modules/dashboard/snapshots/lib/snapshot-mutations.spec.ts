import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { BalanceType } from '@/modules/balances/types/balances';
import { BalanceSnapshot, LocationDataSnapshot, type Snapshot } from '@/modules/dashboard/snapshots';
import { rebuildSnapshotAfterBalanceChange } from '@/modules/dashboard/snapshots/lib/snapshot-mutations';

function balance(usdValue: string, category: BalanceType = BalanceType.ASSET): BalanceSnapshot {
  return BalanceSnapshot.parse({ amount: '1', assetIdentifier: 'ETH', category, timestamp: 1700000000, usdValue });
}

function location(loc: string, usdValue: string): LocationDataSnapshot {
  return LocationDataSnapshot.parse({ location: loc, timestamp: 1700000000, usdValue });
}

function snapshot(balances: BalanceSnapshot[], locations: LocationDataSnapshot[]): Snapshot {
  return { balancesSnapshot: balances, locationDataSnapshot: locations };
}

describe('modules/dashboard/snapshots/lib/snapshot-mutations', () => {
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
});
