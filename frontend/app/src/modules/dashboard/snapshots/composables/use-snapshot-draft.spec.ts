import type { BalanceSnapshot, LocationDataSnapshot, Snapshot } from '@/modules/dashboard/snapshots';
import { bigNumberify } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, ref } from 'vue';
import { BalanceType } from '@/modules/balances/types/balances';
import { useSnapshotDraft } from '@/modules/dashboard/snapshots/composables/use-snapshot-draft';
import { getTotalValue } from '@/modules/dashboard/snapshots/utils/snapshot-totals';

const TS = 1_600_000_000;

function balance(assetIdentifier: string, usdValue: number, category: BalanceType = BalanceType.ASSET): BalanceSnapshot {
  return { amount: bigNumberify(1), assetIdentifier, category, timestamp: TS, usdValue: bigNumberify(usdValue) };
}

function location(name: string, usdValue: number): LocationDataSnapshot {
  return { location: name, timestamp: TS, usdValue: bigNumberify(usdValue) };
}

function snapshot(): Snapshot {
  return {
    balancesSnapshot: [balance('BTC', 100), balance('ETH', 50)],
    locationDataSnapshot: [location('kraken', 100), location('ledger', 50), location('total', 150)],
  };
}

describe('modules/dashboard/snapshots/composables/use-snapshot-draft', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should seed draft and original from the initial snapshot', () => {
    const { dirtyCount, draft, isDirty, original } = useSnapshotDraft(snapshot());

    expect(get(draft)?.balancesSnapshot).toHaveLength(2);
    expect(get(original)?.balancesSnapshot).toHaveLength(2);
    expect(get(isDirty)).toBe(false);
    expect(get(dirtyCount)).toBe(0);
  });

  it('should become dirty after a balance edit and leave original intact', () => {
    const { dirtyCount, draft, editBalance, isDirty, original } = useSnapshotDraft(snapshot());

    editBalance(0, { balance: balance('BTC', 200), location: 'kraken' });

    expect(get(draft)?.balancesSnapshot[0].usdValue.toNumber()).toBe(200);
    expect(get(original)?.balancesSnapshot[0].usdValue.toNumber()).toBe(100);
    expect(get(isDirty)).toBe(true);
    expect(get(dirtyCount)).toBeGreaterThan(0);
  });

  it('should reverse the last mutation with undo', () => {
    const { canUndo, draft, editBalance, isDirty, undo } = useSnapshotDraft(snapshot());

    editBalance(0, { balance: balance('BTC', 200), location: 'kraken' });
    expect(get(canUndo)).toBe(true);

    undo();

    expect(get(draft)?.balancesSnapshot[0].usdValue.toNumber()).toBe(100);
    expect(get(isDirty)).toBe(false);
    expect(get(canUndo)).toBe(false);
  });

  it('should bulk-delete balances in a single undo step', () => {
    const base: Snapshot = {
      balancesSnapshot: [balance('BTC', 100), balance('SPAM', 0), balance('ETH', 50), balance('JUNK', 0)],
      locationDataSnapshot: [location('kraken', 100), location('ledger', 50), location('total', 150)],
    };
    const { canUndo, deleteBalances, draft, undo } = useSnapshotDraft(base);

    deleteBalances([1, 3]);

    expect(get(draft)?.balancesSnapshot.map(item => item.assetIdentifier)).toEqual(['BTC', 'ETH']);
    expect(getTotalValue(get(draft)!.locationDataSnapshot).toNumber()).toBe(150);

    undo();

    expect(get(draft)?.balancesSnapshot).toHaveLength(4);
    expect(get(canUndo)).toBe(false);
  });

  it('should ignore a bulk delete with no indices', () => {
    const { canUndo, deleteBalances, isDirty } = useSnapshotDraft(snapshot());

    deleteBalances([]);

    expect(get(isDirty)).toBe(false);
    expect(get(canUndo)).toBe(false);
  });

  it('should step back one mutation at a time', () => {
    const { addLocation, draft, editBalance, undo } = useSnapshotDraft(snapshot());

    editBalance(0, { balance: balance('BTC', 200), location: 'kraken' });
    addLocation(location('binance', 25));
    expect(get(draft)?.locationDataSnapshot).toHaveLength(4);

    undo();
    expect(get(draft)?.locationDataSnapshot).toHaveLength(3);
    expect(get(draft)?.balancesSnapshot[0].usdValue.toNumber()).toBe(200);

    undo();
    expect(get(draft)?.balancesSnapshot[0].usdValue.toNumber()).toBe(100);
  });

  it('should reset to the original and clear undo on discard', () => {
    const { canUndo, discard, draft, editBalance, isDirty } = useSnapshotDraft(snapshot());

    editBalance(0, { balance: balance('BTC', 200), location: 'kraken' });
    discard();

    expect(get(isDirty)).toBe(false);
    expect(get(canUndo)).toBe(false);
    expect(get(draft)?.balancesSnapshot[0].usdValue.toNumber()).toBe(100);
  });

  it('should expose the sum mismatch of the current draft', () => {
    const { editLocation, mismatch } = useSnapshotDraft(snapshot());

    expect(get(mismatch)).toBeNull();
    editLocation(0, location('kraken', 999));
    expect(get(mismatch)).not.toBeNull();
    expect(get(mismatch)?.locationsSum.toNumber()).toBe(1049);
  });

  it('should reconcile off locations by absorbing the difference', () => {
    // B = 100; locations 60 + 20 = 80. The total is corrected to 100 on load, but
    // the locations still sum to 80, so the snapshot reads as mismatched.
    const base: Snapshot = {
      balancesSnapshot: [balance('BTC', 100)],
      locationDataSnapshot: [location('kraken', 60), location('ledger', 20), location('total', 80)],
    };
    const { draft, mismatch, reconcileLocations } = useSnapshotDraft(base);
    expect(get(mismatch)).not.toBeNull();

    reconcileLocations('kraken');

    expect(get(mismatch)).toBeNull();
    expect(get(draft)!.locationDataSnapshot.find(l => l.location === 'kraken')?.usdValue.toNumber()).toBe(80); // 60 + 20
  });

  it('should rewrite location rows on distributeLocations without touching the total', () => {
    const { distributeLocations, draft } = useSnapshotDraft(snapshot());

    distributeLocations([
      { location: 'kraken', usdValue: bigNumberify(90) },
      { location: 'binance', usdValue: bigNumberify(60) },
    ]);

    const rows = get(draft)!.locationDataSnapshot;
    expect(rows.find(item => item.location === 'kraken')?.usdValue.toNumber()).toBe(90);
    expect(rows.find(item => item.location === 'binance')?.usdValue.toNumber()).toBe(60);
    expect(getTotalValue(rows).toNumber()).toBe(150);
  });

  it('should undo a distributeLocations mutation', () => {
    const { distributeLocations, draft, undo } = useSnapshotDraft(snapshot());

    distributeLocations([{ location: 'kraken', usdValue: bigNumberify(90) }]);
    expect(get(draft)!.locationDataSnapshot.find(item => item.location === 'kraken')?.usdValue.toNumber()).toBe(90);

    undo();
    expect(get(draft)!.locationDataSnapshot.find(item => item.location === 'kraken')?.usdValue.toNumber()).toBe(100);
  });

  it('should commit via the save function and clear the dirty state on success', async () => {
    const { commit, dirtyCount, editBalance, isDirty, original } = useSnapshotDraft(snapshot());
    const saveFn = vi.fn().mockResolvedValue(true);

    editBalance(0, { balance: balance('BTC', 200), location: 'kraken' });
    const result = await commit(saveFn);

    expect(result).toBe(true);
    expect(saveFn).toHaveBeenCalledOnce();
    expect(get(isDirty)).toBe(false);
    expect(get(dirtyCount)).toBe(0);
    expect(get(original)?.balancesSnapshot[0].usdValue.toNumber()).toBe(200);
  });

  it('should preserve the draft and undo stack when the save fails', async () => {
    const { canUndo, commit, draft, editBalance, isDirty } = useSnapshotDraft(snapshot());
    const saveFn = vi.fn().mockResolvedValue(false);

    editBalance(0, { balance: balance('BTC', 200), location: 'kraken' });
    const result = await commit(saveFn);

    expect(result).toBe(false);
    expect(get(isDirty)).toBe(true);
    expect(get(canUndo)).toBe(true);
    expect(get(draft)?.balancesSnapshot[0].usdValue.toNumber()).toBe(200);
  });

  it('should not exclude NFTs when the stored total matches the full balances', () => {
    const { excludeNfts } = useSnapshotDraft(snapshot());
    expect(get(excludeNfts)).toBe(false);
  });

  it('should infer NFT exclusion when the total matches assets minus NFTs', () => {
    const snap: Snapshot = {
      balancesSnapshot: [balance('BTC', 100), balance('_nft_0xabc_1', 40)],
      locationDataSnapshot: [location('total', 100)],
    };
    const { excludeNfts } = useSnapshotDraft(snap);
    expect(get(excludeNfts)).toBe(true);
  });

  it('should correct a stale stored total to the balances on load without marking dirty', () => {
    const snap: Snapshot = {
      balancesSnapshot: [balance('BTC', 100), balance('ETH', 50)],
      locationDataSnapshot: [location('kraken', 100), location('ledger', 50), location('total', 999)],
    };
    const { draft, isDirty } = useSnapshotDraft(snap);
    // Net worth always tracks the balances: the stale 999 total is corrected to 150 on load.
    expect(getTotalValue(get(draft)!.locationDataSnapshot).toNumber()).toBe(150);
    expect(get(isDirty)).toBe(false);
  });

  it('should auto-retrack the total after a balance edit', () => {
    const { draft, editBalance } = useSnapshotDraft(snapshot());
    editBalance(0, { balance: balance('BTC', 200), location: 'kraken' });
    expect(getTotalValue(get(draft)!.locationDataSnapshot).toNumber()).toBe(250);
  });

  it('should re-derive the total when toggling exclude-NFTs and restore it on undo', () => {
    const snap: Snapshot = {
      balancesSnapshot: [balance('BTC', 100), balance('_nft_0xabc_1', 40)],
      locationDataSnapshot: [location('total', 140)],
    };
    const { draft, excludeNfts, undo } = useSnapshotDraft(snap);

    set(excludeNfts, true);
    expect(getTotalValue(get(draft)!.locationDataSnapshot).toNumber()).toBe(100);

    undo();
    expect(get(excludeNfts)).toBe(false);
    expect(getTotalValue(get(draft)!.locationDataSnapshot).toNumber()).toBe(140);
  });

  it('should expose the structured change list', () => {
    const { changes, editBalance } = useSnapshotDraft(snapshot());
    expect(get(changes)).toEqual([]);
    editBalance(0, { balance: balance('BTC', 200), location: 'kraken' });
    expect(get(changes).length).toBeGreaterThan(0);
  });

  it('should re-seed when the initial snapshot changes', async () => {
    const initial = ref<Snapshot | undefined>(snapshot());
    const { draft, editBalance, isDirty } = useSnapshotDraft(initial);

    editBalance(0, { balance: balance('BTC', 200), location: 'kraken' });
    expect(get(isDirty)).toBe(true);

    set(initial, {
      balancesSnapshot: [balance('SOL', 10)],
      locationDataSnapshot: [location('total', 10)],
    });
    await nextTick();

    expect(get(isDirty)).toBe(false);
    expect(get(draft)?.balancesSnapshot[0].assetIdentifier).toBe('SOL');
  });
});
