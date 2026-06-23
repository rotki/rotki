import type { BalanceSnapshot, LocationDataSnapshot, Snapshot } from '@/modules/dashboard/snapshots';
import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { BalanceType } from '@/modules/balances/types/balances';
import {
  applyBalanceAdd,
  applyBalanceDelete,
  applyBalanceEdit,
  applyLocationAdd,
  applyLocationDelete,
  applyLocationEdit,
  applySetTotal,
  buildSnapshotChanges,
  countSnapshotChanges,
  distributeToLocations,
  findSumMismatch,
  snapshotsEqual,
} from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { getTotalValue, locationsTotal } from '@/modules/dashboard/snapshots/utils/snapshot-totals';

const TS = 1_600_000_000;

function balance(
  assetIdentifier: string,
  usdValue: number,
  category: BalanceType = BalanceType.ASSET,
): BalanceSnapshot {
  return {
    amount: bigNumberify(1),
    assetIdentifier,
    category,
    timestamp: TS,
    usdValue: bigNumberify(usdValue),
  };
}

function location(name: string, usdValue: number): LocationDataSnapshot {
  return { location: name, timestamp: TS, usdValue: bigNumberify(usdValue) };
}

function snapshot(): Snapshot {
  return {
    balancesSnapshot: [
      balance('BTC', 100),
      balance('ETH', 50),
    ],
    locationDataSnapshot: [
      location('kraken', 100),
      location('ledger', 50),
      location('total', 150),
    ],
  };
}

describe('modules/dashboard/snapshots/utils/snapshot-math', () => {
  describe('applyBalanceAdd', () => {
    it('should append the balance without mutating the original', () => {
      const original = snapshot();
      const result = applyBalanceAdd(original, { balance: balance('USDC', 20), location: 'kraken' });

      expect(result.balancesSnapshot).toHaveLength(3);
      expect(original.balancesSnapshot).toHaveLength(2);
      expect(result.balancesSnapshot[2].assetIdentifier).toBe('USDC');
    });

    it('should credit the target location subtotal', () => {
      const result = applyBalanceAdd(snapshot(), { balance: balance('USDC', 20), location: 'kraken' });
      const kraken = result.locationDataSnapshot.find(item => item.location === 'kraken');
      expect(kraken?.usdValue.toNumber()).toBe(120);
    });

    it('should create a new location row when it does not exist yet', () => {
      const result = applyBalanceAdd(snapshot(), { balance: balance('USDC', 20), location: 'binance' });
      const binance = result.locationDataSnapshot.find(item => item.location === 'binance');
      expect(binance?.usdValue.toNumber()).toBe(20);
    });

    it('should recompute the stored total from the net balances', () => {
      const result = applyBalanceAdd(snapshot(), { balance: balance('USDC', 20), location: 'kraken' });
      expect(getTotalValue(result.locationDataSnapshot).toNumber()).toBe(170);
    });

    it('should subtract a liability from the total', () => {
      const result = applyBalanceAdd(snapshot(), { balance: balance('DAI', 20, BalanceType.LIABILITY), location: 'kraken' });
      expect(getTotalValue(result.locationDataSnapshot).toNumber()).toBe(130);
    });

    it('should skip location updates when no location is given', () => {
      const result = applyBalanceAdd(snapshot(), { balance: balance('USDC', 20), location: '' });
      expect(result.locationDataSnapshot.find(item => item.location === 'kraken')?.usdValue.toNumber()).toBe(100);
      expect(getTotalValue(result.locationDataSnapshot).toNumber()).toBe(170);
    });
  });

  describe('applyBalanceEdit', () => {
    it('should replace the balance at the index', () => {
      const result = applyBalanceEdit(snapshot(), 0, { balance: balance('BTC', 200), location: 'kraken' });
      expect(result.balancesSnapshot[0].usdValue.toNumber()).toBe(200);
    });

    it('should apply the subtotal delta of remove-old-then-add-new', () => {
      // kraken=100, BTC was 100 -> now 200, so +100
      const result = applyBalanceEdit(snapshot(), 0, { balance: balance('BTC', 200), location: 'kraken' });
      expect(result.locationDataSnapshot.find(item => item.location === 'kraken')?.usdValue.toNumber()).toBe(200);
    });

    it('should recompute the total after an edit', () => {
      const result = applyBalanceEdit(snapshot(), 0, { balance: balance('BTC', 200), location: 'kraken' });
      expect(getTotalValue(result.locationDataSnapshot).toNumber()).toBe(250);
    });

    it('should handle editing an asset into a liability', () => {
      const result = applyBalanceEdit(snapshot(), 0, { balance: balance('BTC', 100, BalanceType.LIABILITY), location: 'kraken' });
      // total = -100 + 50 = -50
      expect(getTotalValue(result.locationDataSnapshot).toNumber()).toBe(-50);
    });
  });

  describe('applyBalanceDelete', () => {
    it('should remove the balance at the index', () => {
      const result = applyBalanceDelete(snapshot(), 0, 'kraken');
      expect(result.balancesSnapshot).toHaveLength(1);
      expect(result.balancesSnapshot[0].assetIdentifier).toBe('ETH');
    });

    it('should debit the location subtotal by the removed asset', () => {
      const result = applyBalanceDelete(snapshot(), 0, 'kraken');
      expect(result.locationDataSnapshot.find(item => item.location === 'kraken')?.usdValue.toNumber()).toBe(0);
    });

    it('should add back a removed liability to the location subtotal', () => {
      const base: Snapshot = {
        balancesSnapshot: [balance('DAI', 30, BalanceType.LIABILITY)],
        locationDataSnapshot: [location('kraken', -30), location('total', -30)],
      };
      const result = applyBalanceDelete(base, 0, 'kraken');
      expect(result.locationDataSnapshot.find(item => item.location === 'kraken')?.usdValue.toNumber()).toBe(0);
    });

    it('should recompute the total after a delete', () => {
      const result = applyBalanceDelete(snapshot(), 0, 'kraken');
      expect(getTotalValue(result.locationDataSnapshot).toNumber()).toBe(50);
    });
  });

  describe('location ops', () => {
    it('should append a location row', () => {
      const result = applyLocationAdd(snapshot(), location('binance', 25));
      expect(result.locationDataSnapshot).toHaveLength(4);
      expect(locationsTotal(result.locationDataSnapshot).toNumber()).toBe(175);
    });

    it('should edit a location row without touching the total', () => {
      const result = applyLocationEdit(snapshot(), 0, location('kraken', 999));
      expect(result.locationDataSnapshot[0].usdValue.toNumber()).toBe(999);
      expect(getTotalValue(result.locationDataSnapshot).toNumber()).toBe(150);
    });

    it('should delete a location row', () => {
      const result = applyLocationDelete(snapshot(), 1);
      expect(result.locationDataSnapshot.find(item => item.location === 'ledger')).toBeUndefined();
    });

    it('should not mutate the original on location ops', () => {
      const original = snapshot();
      applyLocationDelete(original, 0);
      expect(original.locationDataSnapshot).toHaveLength(3);
    });
  });

  describe('applySetTotal', () => {
    it('should set an existing total row', () => {
      const result = applySetTotal(snapshot(), bigNumberify(999));
      expect(getTotalValue(result.locationDataSnapshot).toNumber()).toBe(999);
    });

    it('should create a total row when absent', () => {
      const base: Snapshot = {
        balancesSnapshot: [balance('BTC', 100)],
        locationDataSnapshot: [location('kraken', 100)],
      };
      const result = applySetTotal(base, bigNumberify(123));
      expect(getTotalValue(result.locationDataSnapshot).toNumber()).toBe(123);
    });

    it('should leave the real location rows untouched', () => {
      const result = applySetTotal(snapshot(), bigNumberify(999));
      expect(locationsTotal(result.locationDataSnapshot).toNumber()).toBe(150);
    });
  });

  describe('findSumMismatch', () => {
    it('should return null when all three totals agree', () => {
      expect(findSumMismatch(snapshot())).toBeNull();
    });

    it('should surface a mismatch between locations and the stored total', () => {
      const base = snapshot();
      base.locationDataSnapshot = [location('kraken', 100), location('ledger', 80), location('total', 150)];
      const mismatch = findSumMismatch(base);
      expect(mismatch).not.toBeNull();
      expect(mismatch?.locationsSum.toNumber()).toBe(180);
      expect(mismatch?.storedTotal.toNumber()).toBe(150);
      expect(mismatch?.balancesSum.toNumber()).toBe(150);
    });

    it('should ignore sub-cent drift within the default epsilon', () => {
      const base = snapshot();
      base.locationDataSnapshot = [location('kraken', 100), location('ledger', 50.005), location('total', 150)];
      expect(findSumMismatch(base)).toBeNull();
    });

    it('should respect a custom epsilon', () => {
      const base = snapshot();
      base.locationDataSnapshot = [location('kraken', 100), location('ledger', 55), location('total', 150)];
      expect(findSumMismatch(base, bigNumberify(10))).toBeNull();
      expect(findSumMismatch(base, bigNumberify(1))).not.toBeNull();
    });
  });

  describe('countSnapshotChanges / snapshotsEqual', () => {
    it('should report zero changes for an unmodified copy', () => {
      const original = snapshot();
      expect(countSnapshotChanges(original, snapshot())).toBe(0);
      expect(snapshotsEqual(original, snapshot())).toBe(true);
    });

    it('should count an edited balance', () => {
      const result = applyBalanceEdit(snapshot(), 0, { balance: balance('BTC', 200), location: 'kraken' });
      // BTC value changed + kraken subtotal changed + total changed = 3
      expect(countSnapshotChanges(snapshot(), result)).toBe(3);
      expect(snapshotsEqual(snapshot(), result)).toBe(false);
    });

    it('should count an added balance', () => {
      const original = snapshot();
      const result = { ...original, balancesSnapshot: [...original.balancesSnapshot, balance('USDC', 20)] };
      expect(countSnapshotChanges(original, result)).toBe(1);
    });

    it('should count a removed location', () => {
      const result = applyLocationDelete(snapshot(), 1);
      expect(countSnapshotChanges(snapshot(), result)).toBe(1);
    });

    it('should count a changed stored total only', () => {
      const result = applySetTotal(snapshot(), bigNumberify(999));
      expect(countSnapshotChanges(snapshot(), result)).toBe(1);
    });
  });

  describe('multi-location split', () => {
    it('should split an added balance across locations', () => {
      const result = applyBalanceAdd(snapshot(), {
        balance: balance('SOL', 100),
        location: [location('kraken', 60), location('ledger', 40)].map(l => ({ location: l.location, usdValue: l.usdValue })),
      });
      expect(locationsTotal(result.locationDataSnapshot).toNumber()).toBe(250); // 160 + 90
      expect(result.locationDataSnapshot.find(l => l.location === 'kraken')?.usdValue.toNumber()).toBe(160);
      expect(result.locationDataSnapshot.find(l => l.location === 'ledger')?.usdValue.toNumber()).toBe(90);
      // total tracks the net of all balances regardless of how it is split
      expect(getTotalValue(result.locationDataSnapshot).toNumber()).toBe(250);
    });

    it('should create new location rows from a split', () => {
      const result = applyBalanceAdd(snapshot(), {
        balance: balance('SOL', 30),
        location: [{ location: 'coinbase', usdValue: bigNumberify(10) }, { location: 'binance', usdValue: bigNumberify(20) }],
      });
      expect(result.locationDataSnapshot.find(l => l.location === 'coinbase')?.usdValue.toNumber()).toBe(10);
      expect(result.locationDataSnapshot.find(l => l.location === 'binance')?.usdValue.toNumber()).toBe(20);
    });

    it('should credit each location its share when an edit raises the value', () => {
      // BTC 100 -> 200 (delta +100), split as +60 kraken / +40 ledger.
      const result = applyBalanceEdit(snapshot(), 0, {
        balance: balance('BTC', 200),
        location: [{ location: 'kraken', usdValue: bigNumberify(60) }, { location: 'ledger', usdValue: bigNumberify(40) }],
      });
      // each location moves only by its own delta — the stale old value is not
      // dumped onto the first row.
      expect(result.locationDataSnapshot.find(l => l.location === 'kraken')?.usdValue.toNumber()).toBe(160); // 100 + 60
      expect(result.locationDataSnapshot.find(l => l.location === 'ledger')?.usdValue.toNumber()).toBe(90); // 50 + 40
      expect(getTotalValue(result.locationDataSnapshot).toNumber()).toBe(250); // 200 + 50
    });

    it('should debit each location its share when an edit lowers the value', () => {
      // BTC 100 -> 20 (delta -80), split as -50 kraken / -30 ledger (negated by
      // the dialog from the positive removal amounts the user enters).
      const result = applyBalanceEdit(snapshot(), 0, {
        balance: balance('BTC', 20),
        location: [{ location: 'kraken', usdValue: bigNumberify(-50) }, { location: 'ledger', usdValue: bigNumberify(-30) }],
      });
      expect(result.locationDataSnapshot.find(l => l.location === 'kraken')?.usdValue.toNumber()).toBe(50); // 100 - 50
      expect(result.locationDataSnapshot.find(l => l.location === 'ledger')?.usdValue.toNumber()).toBe(20); // 50 - 30
      expect(getTotalValue(result.locationDataSnapshot).toNumber()).toBe(70); // 20 + 50
    });

    it('should behave identically to the single-location path for one entry', () => {
      const viaString = applyBalanceAdd(snapshot(), { balance: balance('SOL', 100), location: 'kraken' });
      const viaSplit = applyBalanceAdd(snapshot(), { balance: balance('SOL', 100), location: [{ location: 'kraken', usdValue: bigNumberify(100) }] });
      expect(viaSplit.locationDataSnapshot).toEqual(viaString.locationDataSnapshot);
    });

    it('should debit each location by its share when deleting with a split', () => {
      // BTC (100) split 70/30 across kraken/ledger; deleting unwinds each share.
      const result = applyBalanceDelete(snapshot(), 0, [
        { location: 'kraken', usdValue: bigNumberify(70) },
        { location: 'ledger', usdValue: bigNumberify(30) },
      ]);
      expect(result.balancesSnapshot).toHaveLength(1);
      expect(result.locationDataSnapshot.find(l => l.location === 'kraken')?.usdValue.toNumber()).toBe(30); // 100 - 70
      expect(result.locationDataSnapshot.find(l => l.location === 'ledger')?.usdValue.toNumber()).toBe(20); // 50 - 30
    });

    it('should add back each share when deleting a split liability', () => {
      const base: Snapshot = {
        balancesSnapshot: [balance('DAI', 30, BalanceType.LIABILITY)],
        locationDataSnapshot: [location('kraken', -20), location('ledger', -10), location('total', -30)],
      };
      const result = applyBalanceDelete(base, 0, [
        { location: 'kraken', usdValue: bigNumberify(20) },
        { location: 'ledger', usdValue: bigNumberify(10) },
      ]);
      expect(result.locationDataSnapshot.find(l => l.location === 'kraken')?.usdValue.toNumber()).toBe(0); // -20 + 20
      expect(result.locationDataSnapshot.find(l => l.location === 'ledger')?.usdValue.toNumber()).toBe(0); // -10 + 10
    });

    it('should match the single-location delete for one entry', () => {
      const viaString = applyBalanceDelete(snapshot(), 0, 'kraken');
      const viaSplit = applyBalanceDelete(snapshot(), 0, [{ location: 'kraken', usdValue: bigNumberify(100) }]);
      expect(viaSplit.locationDataSnapshot).toEqual(viaString.locationDataSnapshot);
    });
  });

  describe('distributeToLocations', () => {
    it('should set absolute subtotals and leave the total untouched', () => {
      const result = distributeToLocations(snapshot(), [location('kraken', 130), location('ledger', 20)]);
      expect(result.locationDataSnapshot.find(l => l.location === 'kraken')?.usdValue.toNumber()).toBe(130);
      expect(result.locationDataSnapshot.find(l => l.location === 'ledger')?.usdValue.toNumber()).toBe(20);
      expect(getTotalValue(result.locationDataSnapshot).toNumber()).toBe(150);
    });

    it('should create rows for unknown locations', () => {
      const result = distributeToLocations(snapshot(), [{ location: 'coinbase', usdValue: bigNumberify(75) }]);
      expect(result.locationDataSnapshot.find(l => l.location === 'coinbase')?.usdValue.toNumber()).toBe(75);
    });

    it('should not mutate the original', () => {
      const original = snapshot();
      distributeToLocations(original, [location('kraken', 999)]);
      expect(original.locationDataSnapshot.find(l => l.location === 'kraken')?.usdValue.toNumber()).toBe(100);
    });
  });

  describe('buildSnapshotChanges', () => {
    it('should return an empty list for an unmodified copy', () => {
      expect(buildSnapshotChanges(snapshot(), snapshot())).toEqual([]);
    });

    it('should describe a balance edit, its location and the derived total', () => {
      const result = applyBalanceEdit(snapshot(), 0, { balance: balance('BTC', 200), location: 'kraken' });
      const changes = buildSnapshotChanges(snapshot(), result);

      expect(changes).toHaveLength(3);
      expect(changes.find(c => c.kind === 'balance-changed')).toMatchObject({ index: 0, kind: 'balance-changed' });
      expect(changes.find(c => c.kind === 'location-changed')).toMatchObject({ kind: 'location-changed', location: 'kraken' });
      const total = changes.find(c => c.kind === 'total-changed');
      expect(total).toBeDefined();
      expect(total?.kind === 'total-changed' && total.after.toNumber()).toBe(250);
    });

    it('should describe an added balance', () => {
      const original = snapshot();
      const result = { ...original, balancesSnapshot: [...original.balancesSnapshot, balance('USDC', 20)] };
      const changes = buildSnapshotChanges(original, result);
      expect(changes).toEqual([{ after: balance('USDC', 20), index: 2, kind: 'balance-added' }]);
    });

    it('should match balances by identity, not index, when an earlier row is removed', () => {
      const original = snapshot();
      // Drop BTC (index 0); ETH shifts from index 1 to 0 but is otherwise unchanged.
      const result = { ...original, balancesSnapshot: [balance('ETH', 50)] };
      const changes = buildSnapshotChanges(original, result);
      // Only BTC's removal — ETH's index shift must NOT register as a change.
      expect(changes).toEqual([{ before: balance('BTC', 100), index: 0, kind: 'balance-removed' }]);
    });

    it('should describe a removed location', () => {
      const result = applyLocationDelete(snapshot(), 1);
      const changes = buildSnapshotChanges(snapshot(), result);
      expect(changes).toHaveLength(1);
      expect(changes[0]).toMatchObject({ kind: 'location-removed', location: 'ledger' });
    });

    it('should surface a manual total change as total-changed', () => {
      const result = applySetTotal(snapshot(), bigNumberify(999));
      const changes = buildSnapshotChanges(snapshot(), result);
      expect(changes).toEqual([{ after: bigNumberify(999), before: bigNumberify(150), kind: 'total-changed' }]);
    });
  });
});
