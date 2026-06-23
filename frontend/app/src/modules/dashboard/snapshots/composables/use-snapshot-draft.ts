import type { BigNumber } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter, Ref, WritableComputedRef } from 'vue';
import type { LocationDataSnapshot, Snapshot } from '@/modules/dashboard/snapshots';
import {
  applyBalanceAdd,
  applyBalanceDelete,
  applyBalanceEdit,
  applyLocationAdd,
  applyLocationDelete,
  applyLocationEdit,
  applySetTotal,
  approxEqualUsd,
  type BalanceMutation,
  buildSnapshotChanges,
  cloneSnapshot,
  countSnapshotChanges,
  distributeToLocations,
  findSumMismatch,
  type LocationAttribution,
  type LocationSplit,
  type SnapshotChange,
  snapshotsEqual,
  type SnapshotSumMismatch,
} from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { applyBalanceBulkDelete, applyReconcileLocations } from '@/modules/dashboard/snapshots/utils/snapshot-mutations';
import { assetsTotal, getTotalValue, nftsTotal } from '@/modules/dashboard/snapshots/utils/snapshot-totals';

/** Maximum depth of the undo history (full draft states). */
const UNDO_LIMIT = 50;

/** A full undo entry: the draft plus the NFT-exclusion flag at that point. */
interface DraftState {
  snapshot: Snapshot;
  /** Whether NFTs are excluded from the tracked net worth at this point. */
  excludeNfts: boolean;
}

interface UseSnapshotDraftReturn {
  draft: Ref<Snapshot | undefined>;
  original: Ref<Snapshot | undefined>;
  isDirty: ComputedRef<boolean>;
  dirtyCount: ComputedRef<number>;
  changes: ComputedRef<SnapshotChange[]>;
  mismatch: ComputedRef<SnapshotSumMismatch | null>;
  canUndo: ComputedRef<boolean>;
  /** Whether NFTs are excluded from the (always auto-tracked) net worth (writable). */
  excludeNfts: WritableComputedRef<boolean>;
  addBalance: (mutation: BalanceMutation) => void;
  editBalance: (index: number, mutation: BalanceMutation) => void;
  deleteBalance: (index: number, location: LocationAttribution) => void;
  /** Removes several balance rows in one undo step (used for the zero-value sweep). */
  deleteBalances: (indices: number[]) => void;
  addLocation: (location: LocationDataSnapshot) => void;
  editLocation: (index: number, location: LocationDataSnapshot) => void;
  deleteLocation: (index: number) => void;
  distributeLocations: (splits: LocationSplit[]) => void;
  /** One-click fix for off location subtotals: absorb the difference into `location` so they sum to the net worth. */
  reconcileLocations: (location: string) => void;
  undo: () => void;
  discard: () => void;
  commit: (saveFn: (snapshot: Snapshot) => Promise<boolean>) => Promise<boolean>;
}

/**
 * The snapshot editor's brain. Owns a local `draft`, the last-saved `original`,
 * an undo history, and the total-tracking *mode*. Every mutation dispatches to
 * the pure `snapshot-math` transforms (no Vue, no I/O), so dirtiness, the
 * change list, the sum mismatch and undo are all derived deterministically.
 *
 * Net worth ALWAYS tracks the balances (assets − liabilities, minus NFTs when
 * excluded) — the balances are the source of truth, so there is no manual total.
 * The stored total is corrected to the balances on load and re-tracked after
 * every balance mutation; only the NFT-exclusion flag is inferred on load.
 *
 * Undo uses a bounded full-state stack (snapshot + the NFT flag) rather than
 * op-inversion — simpler and impossible to desync for the v1 editor.
 *
 * @param initial the loaded snapshot (value, ref or getter); re-seeds the draft
 *   whenever it changes (e.g. navigating to a different snapshot).
 */
export function useSnapshotDraft(initial: MaybeRefOrGetter<Snapshot | undefined>): UseSnapshotDraftReturn {
  const original = ref<Snapshot>();
  const draft = ref<Snapshot>();
  const undoStack = ref<DraftState[]>([]);

  const excludeNftsState = shallowRef<boolean>(false);

  /**
   * Infers whether a freshly loaded snapshot's stored total excludes NFT value:
   * true only when it clearly tracks assets-minus-NFTs rather than full assets.
   */
  function inferExcludeNfts(snapshot: Snapshot): void {
    const assets = assetsTotal(snapshot.balancesSnapshot);
    const stored = getTotalValue(snapshot.locationDataSnapshot);
    const tracksFullAssets = approxEqualUsd(stored, assets);
    const tracksAssetsExNfts = approxEqualUsd(stored, assets.minus(nftsTotal(snapshot.balancesSnapshot)));
    set(excludeNftsState, !tracksFullAssets && tracksAssetsExNfts);
  }

  function reset(snapshot: Snapshot | undefined): void {
    if (!snapshot) {
      set(original, undefined);
      set(draft, undefined);
      set(undoStack, []);
      return;
    }
    inferExcludeNfts(snapshot);
    // Net worth always tracks the balances, so correct the stored total on load
    // (the backend value can be stale). Baseline and draft both hold the
    // corrected snapshot, so a freshly-opened snapshot is never spuriously dirty.
    const corrected = retrackTotal(cloneSnapshot(snapshot));
    set(original, cloneSnapshot(corrected));
    set(draft, cloneSnapshot(corrected));
    set(undoStack, []);
  }

  watch(() => toValue(initial), reset, { immediate: true });

  /** The total the auto-tracker should hold for the given snapshot. */
  function trackedTotal(snapshot: Snapshot): BigNumber {
    const assets = assetsTotal(snapshot.balancesSnapshot);
    return get(excludeNftsState) ? assets.minus(nftsTotal(snapshot.balancesSnapshot)) : assets;
  }

  /**
   * Re-asserts the stored total to the tracked net worth (counteracting the
   * balance-rebuild's recompute). The total always tracks the balances, so this
   * runs on load and after every balance mutation / NFT-flag change.
   */
  function retrackTotal(snapshot: Snapshot): Snapshot {
    return applySetTotal(snapshot, trackedTotal(snapshot));
  }

  /** Pushes the current draft + mode onto the undo stack before a mutation. */
  function pushUndo(): void {
    const current = get(draft);
    if (!current)
      return;
    // Clone for undo: the rebuild helpers mutate location rows in place, which
    // would otherwise corrupt a shared undo entry.
    const entry: DraftState = {
      excludeNfts: get(excludeNftsState),
      snapshot: cloneSnapshot(current),
    };
    set(undoStack, [...get(undoStack), entry].slice(-UNDO_LIMIT));
  }

  /** A plain draft transform (no re-tracking) — for location ops and reconcile. */
  function mutate(transform: (snapshot: Snapshot) => Snapshot): void {
    const current = get(draft);
    if (!current)
      return;
    pushUndo();
    set(draft, transform(current));
  }

  /** A balance transform that re-asserts the tracked total afterwards. */
  function mutateBalance(transform: (snapshot: Snapshot) => Snapshot): void {
    mutate(snapshot => retrackTotal(transform(snapshot)));
  }

  /**
   * A mode change: snapshots the undo entry *before* flipping any flag (so undo
   * restores the prior mode), then optionally re-derives the draft total.
   */
  function changeMode(mutateFlags: () => void, transform?: (snapshot: Snapshot) => Snapshot): void {
    const current = get(draft);
    if (!current)
      return;
    pushUndo();
    mutateFlags();
    if (transform)
      set(draft, transform(current));
  }

  const isDirty = computed<boolean>(() => {
    const a = get(original);
    const b = get(draft);
    if (!a || !b)
      return false;
    return !snapshotsEqual(a, b);
  });

  const dirtyCount = computed<number>(() => {
    const a = get(original);
    const b = get(draft);
    if (!a || !b)
      return 0;
    return countSnapshotChanges(a, b);
  });

  const changes = computed<SnapshotChange[]>(() => {
    const a = get(original);
    const b = get(draft);
    if (!a || !b)
      return [];
    return buildSnapshotChanges(a, b);
  });

  // Compare against the *tracked* net worth (NFT-aware) rather than the full
  // balances, so excluding NFTs doesn't read as a permanent total mismatch.
  const mismatch = computed<SnapshotSumMismatch | null>(() => {
    const current = get(draft);
    return current ? findSumMismatch(current, undefined, trackedTotal(current)) : null;
  });

  const canUndo = computed<boolean>(() => get(undoStack).length > 0);

  function addBalance(mutation: BalanceMutation): void {
    mutateBalance(snapshot => applyBalanceAdd(snapshot, mutation));
  }

  function editBalance(index: number, mutation: BalanceMutation): void {
    mutateBalance(snapshot => applyBalanceEdit(snapshot, index, mutation));
  }

  function deleteBalance(index: number, location: LocationAttribution): void {
    mutateBalance(snapshot => applyBalanceDelete(snapshot, index, location));
  }

  function deleteBalances(indices: number[]): void {
    if (indices.length === 0)
      return;
    mutateBalance(snapshot => applyBalanceBulkDelete(snapshot, indices));
  }

  function addLocation(location: LocationDataSnapshot): void {
    mutate(snapshot => applyLocationAdd(snapshot, location));
  }

  function editLocation(index: number, location: LocationDataSnapshot): void {
    mutate(snapshot => applyLocationEdit(snapshot, index, location));
  }

  function deleteLocation(index: number): void {
    mutate(snapshot => applyLocationDelete(snapshot, index));
  }

  /**
   * Reconcile the allocation by writing each split's USD value onto its location
   * row (creating missing rows). Locations are an independent allocation view, so
   * this never touches the auto-tracked total — it only realigns the venue split.
   */
  function distributeLocations(splits: LocationSplit[]): void {
    mutate(snapshot => distributeToLocations(snapshot, splits));
  }

  /**
   * Reconcile off location subtotals in one step: absorb the discrepancy into
   * `location` so the locations sum to the tracked net worth (and snap the total
   * to it too). The total already auto-tracks the balances, so a later balance
   * edit keeps the snapshot reconciled.
   */
  function reconcileLocations(location: string): void {
    mutate(snapshot => applyReconcileLocations(snapshot, location, trackedTotal(snapshot)));
  }

  function setExcludeNfts(value: boolean): void {
    if (value === get(excludeNftsState))
      return;
    changeMode(() => set(excludeNftsState, value), retrackTotal);
  }

  const excludeNfts = computed<boolean>({
    get: () => get(excludeNftsState),
    set: setExcludeNfts,
  });

  function undo(): void {
    const stack = get(undoStack);
    const previous = stack.at(-1);
    if (!previous)
      return;
    set(undoStack, stack.slice(0, -1));
    set(draft, previous.snapshot);
    set(excludeNftsState, previous.excludeNfts);
  }

  function discard(): void {
    const baseline = get(original);
    set(draft, baseline ? cloneSnapshot(baseline) : undefined);
    set(undoStack, []);
    if (baseline)
      inferExcludeNfts(baseline);
  }

  async function commit(saveFn: (snapshot: Snapshot) => Promise<boolean>): Promise<boolean> {
    const current = get(draft);
    if (!current)
      return false;

    // On failure the draft and undo stack are preserved so the user keeps their
    // work and can retry.
    const success = await saveFn(current);
    if (success) {
      set(original, cloneSnapshot(current));
      set(undoStack, []);
    }
    return success;
  }

  return {
    addBalance,
    addLocation,
    canUndo,
    changes,
    commit,
    deleteBalance,
    deleteBalances,
    deleteLocation,
    discard,
    dirtyCount,
    distributeLocations,
    // exposed writable: bound via v-model in the editor and handed to the pure
    // snapshot-math helpers, which take a plain Snapshot (not DeepReadonly).
    // eslint-disable-next-line @rotki/composable-return-readonly
    draft,
    editBalance,
    editLocation,
    excludeNfts,
    isDirty,
    mismatch,
    // exposed writable: re-seeded on load and compared/cloned by the math helpers.
    // eslint-disable-next-line @rotki/composable-return-readonly
    original,
    reconcileLocations,
    undo,
  };
}
