import type { ComputedRef, MaybeRefOrGetter, Ref, WritableComputedRef } from 'vue';
import type { ActionStatus } from '@/modules/core/common/action';
import type { LocationDataSnapshot, Snapshot } from '@/modules/dashboard/snapshots';
import { inferExcludeNfts, retrackTotal, seedDraft, trackedTotal } from '@/modules/dashboard/snapshots/utils/snapshot-draft-total';
import {
  applyBalanceAdd,
  applyBalanceDelete,
  applyBalanceEdit,
  applyLocationAdd,
  applyLocationDelete,
  applyLocationEdit,
  type BalanceMutation,
  buildSnapshotChanges,
  cloneSnapshot,
  distributeToLocations,
  findSumMismatch,
  type LocationAttribution,
  type LocationSplit,
  type SnapshotDraftChange,
  type SnapshotSumMismatch,
} from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { applyBalanceBulkDelete, applyReconcileLocations } from '@/modules/dashboard/snapshots/utils/snapshot-mutations';

/** Maximum depth of the undo history (full draft states). */
const UNDO_LIMIT = 50;

/** A full undo entry: the draft, the NFT-exclusion flag and the pending spam marks at that point. */
interface DraftState {
  snapshot: Snapshot;
  /** Whether NFTs are excluded from the tracked net worth at this point. */
  excludeNfts: boolean;
  /** Assets to mark as spam on save, as queued at this point. */
  pendingSpam: string[];
}

/**
 * What a {@link UseSnapshotDraftReturn.commit} achieved.
 *
 * @remarks
 * `spamError` says why marking the pending assets as spam failed. The marks stay pending, so the
 * next save retries them.
 */
type SnapshotCommitResult = { saved: false } | { saved: true; spamError?: string };

/** A balance row removal, as the delete dialog confirms it. */
export interface BalanceDeletion {
  index: number;
  location: LocationAttribution;
  /** Also mark the row's asset as spam on save. */
  markSpam: boolean;
}

interface UseSnapshotDraftReturn {
  draft: Readonly<Ref<Snapshot | undefined>>;
  original: Readonly<Ref<Snapshot | undefined>>;
  isDirty: ComputedRef<boolean>;
  dirtyCount: ComputedRef<number>;
  changes: ComputedRef<SnapshotDraftChange[]>;
  mismatch: ComputedRef<SnapshotSumMismatch | null>;
  canUndo: ComputedRef<boolean>;
  /** Whether NFTs are excluded from the (always auto-tracked) net worth (writable). */
  excludeNfts: WritableComputedRef<boolean>;
  addBalance: (mutation: BalanceMutation) => void;
  editBalance: (index: number, mutation: BalanceMutation) => void;
  /**
   * Removes one balance row, debiting `location`.
   *
   * @remarks
   * With `markSpam`, the row's asset is also queued to be marked as spam on save.
   */
  deleteBalance: (index: number, location: LocationAttribution, markSpam?: boolean) => void;
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
  /**
   * Saves the draft, then marks the pending assets as spam.
   *
   * @remarks
   * Nothing is marked unless the snapshot saved. A failed save leaves the draft and the undo stack
   * standing, so the user keeps their work and can retry. A failed spam mark leaves the snapshot
   * saved and the marks pending.
   *
   * @param saveFn - performs the snapshot write, reporting whether it landed
   * @param markSpam - marks the given assets as spam in one batch
   */
  commit: (
    saveFn: (snapshot: Snapshot) => Promise<boolean>,
    markSpam: (assets: string[]) => Promise<ActionStatus>,
  ) => Promise<SnapshotCommitResult>;
}

/**
 * The snapshot editor's brain. Owns a local `draft`, the last-saved `original`,
 * an undo history, and the total-tracking *mode*. Every mutation dispatches to
 * the pure `snapshot-math` transforms (no Vue, no I/O), so dirtiness, the
 * change list, the sum mismatch and undo are all derived deterministically.
 *
 * Net worth ALWAYS tracks the balances (assets − liabilities, minus NFTs when
 * excluded) — the balances are the source of truth, so there is no manual total.
 * A stale stored total is corrected to the balances on load (an unsaved change)
 * and re-tracked after every balance mutation; only the NFT-exclusion flag is
 * inferred on load.
 *
 * Undo uses a bounded full-state stack (snapshot, the NFT flag and the pending
 * spam marks) rather than op-inversion, which is simpler and cannot desync.
 *
 * @param initial - the loaded snapshot, as a value, ref or getter; the draft is re-seeded whenever
 * it changes, such as on navigating to a different snapshot
 */
export function useSnapshotDraft(initial: MaybeRefOrGetter<Snapshot | undefined>): UseSnapshotDraftReturn {
  const original = ref<Snapshot>();
  const draft = ref<Snapshot>();
  const undoStack = ref<DraftState[]>([]);
  const pendingSpam = shallowRef<string[]>([]);

  const excludeNftsState = shallowRef<boolean>(false);

  /** Seeds the draft from `baseline`, dropping the undo history and every pending spam mark. */
  function reseed(baseline: Snapshot | undefined): void {
    if (baseline)
      set(excludeNftsState, inferExcludeNfts(baseline));
    set(draft, baseline ? seedDraft(baseline, get(excludeNftsState)) : undefined);
    set(undoStack, []);
    set(pendingSpam, []);
  }

  /**
   * Opens a snapshot: the baseline as stored, the draft as {@link seedDraft} corrects it.
   *
   * @param snapshot - the snapshot to open, or `undefined` to close the editor
   */
  function reset(snapshot: Snapshot | undefined): void {
    set(original, snapshot ? cloneSnapshot(snapshot) : undefined);
    reseed(snapshot);
  }

  watch(() => toValue(initial), reset, { immediate: true });

  /**
   * Pushes the current draft, mode and pending spam marks onto the undo stack before a mutation.
   *
   * @remarks
   * The snapshot is cloned in, because the rebuild helpers mutate location rows in place and would
   * otherwise corrupt a shared undo entry.
   */
  function pushUndo(): void {
    const current = get(draft);
    if (!current)
      return;
    const entry: DraftState = {
      excludeNfts: get(excludeNftsState),
      pendingSpam: get(pendingSpam),
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
    mutate(snapshot => retrackTotal(transform(snapshot), get(excludeNftsState)));
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

  const changes = computed<SnapshotDraftChange[]>(() => {
    const a = get(original);
    const b = get(draft);
    if (!a || !b)
      return [];
    const marks = get(pendingSpam).map((asset): SnapshotDraftChange => ({ asset, kind: 'spam-marked' }));
    return [...buildSnapshotChanges(a, b), ...marks];
  });

  const dirtyCount = computed<number>(() => get(changes).length);

  const isDirty = computed<boolean>(() => get(dirtyCount) > 0);

  /**
   * Where the locations stop summing to the total, if they do.
   *
   * @remarks
   * Compared against the NFT-aware tracked net worth rather than the full balances, so excluding
   * NFTs does not read as a permanent mismatch.
   */
  const mismatch = computed<SnapshotSumMismatch | null>(() => {
    const current = get(draft);
    return current ? findSumMismatch(current, undefined, trackedTotal(current, get(excludeNftsState))) : null;
  });

  const canUndo = computed<boolean>(() => get(undoStack).length > 0);

  function addBalance(mutation: BalanceMutation): void {
    mutateBalance(snapshot => applyBalanceAdd(snapshot, mutation));
  }

  function editBalance(index: number, mutation: BalanceMutation): void {
    mutateBalance(snapshot => applyBalanceEdit(snapshot, index, mutation));
  }

  function deleteBalance(index: number, location: LocationAttribution, markSpam: boolean = false): void {
    const asset = get(draft)?.balancesSnapshot[index]?.assetIdentifier;
    mutateBalance(snapshot => applyBalanceDelete(snapshot, index, location));
    const pending = get(pendingSpam);
    if (markSpam && asset && !pending.includes(asset))
      set(pendingSpam, [...pending, asset]);
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
    mutate(snapshot => applyReconcileLocations(snapshot, location, trackedTotal(snapshot, get(excludeNftsState))));
  }

  function setExcludeNfts(value: boolean): void {
    if (value === get(excludeNftsState))
      return;
    changeMode(() => set(excludeNftsState, value), snapshot => retrackTotal(snapshot, value));
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
    set(pendingSpam, previous.pendingSpam);
  }

  function discard(): void {
    reseed(get(original));
  }

  async function commit(
    saveFn: (snapshot: Snapshot) => Promise<boolean>,
    markSpam: (assets: string[]) => Promise<ActionStatus>,
  ): Promise<SnapshotCommitResult> {
    const current = get(draft);
    const assets = get(pendingSpam);
    const onlySpamPending = assets.length > 0 && get(dirtyCount) === assets.length;
    if (!current || (!onlySpamPending && !(await saveFn(current))))
      return { saved: false };

    set(original, cloneSnapshot(current));
    set(undoStack, []);
    if (assets.length > 0) {
      const status = await markSpam(assets);
      if (!status.success)
        return { saved: true, spamError: status.message };
      set(pendingSpam, []);
    }
    return { saved: true };
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
    draft: shallowReadonly(draft),
    editBalance,
    editLocation,
    excludeNfts,
    isDirty,
    mismatch,
    original: shallowReadonly(original),
    reconcileLocations,
    undo,
  };
}
