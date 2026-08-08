import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { TaskOrchestrator } from './core/orchestrator/api';
import { createTaskOrchestrator } from './core/orchestrator/orchestrator';
import { ACCOUNT_SYNC_LANE_PREFIX, ACCOUNTS_ADD_LANE_PREFIX, ACCOUNTS_REMOVE_LANE_PREFIX, BALANCES_CACHED_LANE, BALANCES_LANE, CHAIN_SYNC_LANE, DECODE_LANE, EXCHANGE_EVENTS_LANE_PREFIX, EXCHANGE_LANE, SESSION_LANE, UMBRELLA_LANE } from './core/orchestrator/spec';
import { type Activity, type ActivityKind, makeActivityId, type WorkStatus } from './core/types';

/**
 * An activity-id part that may itself be reactive, so a reader whose subject changes (the chain a
 * page is showing) gets one computed instead of rebuilding it per value.
 */
type ActivityPartSource = MaybeRefOrGetter<string | number>;

export interface UseTaskOrchestratorReturn extends TaskOrchestrator {
  /** Reactive projection of the orchestrator's activities, updated on every change. */
  readonly activities: Readonly<Ref<Activity[]>>;
  /**
   * Reactive {@link WorkStatus} for a kind (or the specific id `makeActivityId(kind, ...parts)`).
   * Re-evaluates on every orchestrator change. The reactive replacement for `useStatusUpdater`.
   */
  readonly useWorkStatus: (kind: ActivityKind, ...parts: ActivityPartSource[]) => ComputedRef<WorkStatus>;
  /**
   * Reactive {@link WorkStatus} aggregated over every activity whose id extends `kind:parts`.
   * The reader side of per-request producers: "is *any* historic price fetch in flight".
   */
  readonly useWorkStatusPrefix: (kind: ActivityKind, ...parts: ActivityPartSource[]) => ComputedRef<WorkStatus>;
  /**
   * Just the liveness of {@link useWorkStatus} — "is this work in flight right now".
   *
   * Most readers want a spinner, not the whole snapshot, and were each wrapping the composite in
   * their own `computed(() => get(status).active)`. Reach for {@link useWorkStatus} when a reader
   * needs more than one field: the fields describe one moment and belong together, which is why
   * this returns a second computed rather than the status being split into independent refs.
   */
  readonly useIsActive: (kind: ActivityKind, ...parts: ActivityPartSource[]) => ComputedRef<boolean>;
  /** Liveness of {@link useWorkStatusPrefix} — "is *any* activity under this prefix in flight". */
  readonly useIsActivePrefix: (kind: ActivityKind, ...parts: ActivityPartSource[]) => ComputedRef<boolean>;
  /**
   * Reactive live {@link Activity} for `makeActivityId(kind, ...parts)` — its `steps`/`percentage`
   * are the native progress channel for work whose progress is pushed via {@link reportProgress}.
   * Undefined while no such activity is registered.
   */
  readonly useActivity: (kind: ActivityKind, ...parts: (string | number)[]) => ComputedRef<Activity | undefined>;
  /**
   * Bumped on every orchestrator change, ledger writes included. Touch it inside a computed that
   * calls the non-reactive core directly (`statusOfPrefix` over a list of chains, say) to make that
   * computed re-evaluate; the `useWorkStatus*` helpers already do this for you.
   */
  readonly version: Readonly<Ref<number>>;
}

/**
 * The single shared {@link TaskOrchestrator} instance plus a reactive snapshot of its
 * activities. The orchestrator is framework-agnostic; this is the only seam that turns its
 * change emitter into a Vue ref. Producers submit native work here; the controller cancels /
 * reruns through it.
 */
export const useTaskOrchestrator = createSharedComposable((): UseTaskOrchestratorReturn => {
  const orchestrator = createTaskOrchestrator({
    caps: {
      [BALANCES_CACHED_LANE]: 2,
      [BALANCES_LANE]: 2,
      [CHAIN_SYNC_LANE]: 2,
      [DECODE_LANE]: 2,
      [EXCHANGE_LANE]: 2,
      [SESSION_LANE]: 2,
      [UMBRELLA_LANE]: 16,
    },
    // Two accounts per chain, not two across every chain; one query per exchange location; two
    // addresses added at once per chain, replacing `addMultipleAccounts`'s own limiter. Removals
    // take 1 per chain and 1 active lane, which is the fully serial shape they always had.
    laneFamilies: { [ACCOUNT_SYNC_LANE_PREFIX]: 2, [ACCOUNTS_ADD_LANE_PREFIX]: 2, [ACCOUNTS_REMOVE_LANE_PREFIX]: 1, [EXCHANGE_EVENTS_LANE_PREFIX]: 1 },
    // ...and only two chains' lanes live at once. The accounts of every chain are declared up
    // front now, so without this the per-chain cap alone would let all of them progress together.
    laneFamilyActive: { [ACCOUNT_SYNC_LANE_PREFIX]: 2, [ACCOUNTS_ADD_LANE_PREFIX]: 2, [ACCOUNTS_REMOVE_LANE_PREFIX]: 1, [EXCHANGE_EVENTS_LANE_PREFIX]: 2 },
  });
  const activities = shallowRef<Activity[]>([]);
  // Bumped on every orchestrator change so `useWorkStatus` computeds re-read the (non-reactive)
  // records + ledger. Ledger writes always co-occur with an emit, so this captures freshness too.
  const version = shallowRef<number>(0);

  orchestrator.onChange(() => {
    // Ephemeral activities (pre-login unlock work) are tracked by the orchestrator but never
    // projected into the render model — they must not surface in the task center. Everything
    // else (scheduling, cancel, status queries) still sees them via the complete `snapshot()`.
    set(activities, orchestrator.snapshot().filter(activity => !activity.ephemeral));
    set(version, get(version) + 1);
  });

  function useWorkStatus(kind: ActivityKind, ...parts: ActivityPartSource[]): ComputedRef<WorkStatus> {
    return computed<WorkStatus>(() => {
      get(version); // touch the change counter so the projection recomputes on every mutation
      return orchestrator.statusOf(kind, ...parts.map(part => toValue(part)));
    });
  }

  function useIsActive(kind: ActivityKind, ...parts: ActivityPartSource[]): ComputedRef<boolean> {
    const status = useWorkStatus(kind, ...parts);
    return computed<boolean>(() => get(status).active);
  }

  function useWorkStatusPrefix(kind: ActivityKind, ...parts: ActivityPartSource[]): ComputedRef<WorkStatus> {
    return computed<WorkStatus>(() => {
      get(version); // touch the change counter so the projection recomputes on every mutation
      return orchestrator.statusOfPrefix(kind, ...parts.map(part => toValue(part)));
    });
  }

  function useIsActivePrefix(kind: ActivityKind, ...parts: ActivityPartSource[]): ComputedRef<boolean> {
    const status = useWorkStatusPrefix(kind, ...parts);
    return computed<boolean>(() => get(status).active);
  }

  function useActivity(kind: ActivityKind, ...parts: (string | number)[]): ComputedRef<Activity | undefined> {
    const id = makeActivityId(kind, ...parts);
    return computed<Activity | undefined>(() => get(activities).find(activity => activity.id === id));
  }

  return { ...orchestrator, activities, useActivity, useIsActive, useIsActivePrefix, useWorkStatus, useWorkStatusPrefix, version };
});
