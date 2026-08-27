import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { TaskOrchestrator } from './core/orchestrator/api';
import { createTaskOrchestrator } from './core/orchestrator/orchestrator';
import { ACCOUNT_SYNC_LANE_PREFIX, ACCOUNTS_ADD_LANE_PREFIX, ACCOUNTS_REMOVE_LANE_PREFIX, BALANCES_LANE, CHAIN_SYNC_LANE, DECODE_LANE, DETECT_LANE_PREFIX, EXCHANGE_EVENTS_LANE_PREFIX, EXCHANGE_LANE, SESSION_LANE, UMBRELLA_LANE } from './core/orchestrator/spec';
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
      [BALANCES_LANE]: 2,
      [CHAIN_SYNC_LANE]: 2,
      [DECODE_LANE]: 2,
      [EXCHANGE_LANE]: 2,
      [SESSION_LANE]: 2,
      [UMBRELLA_LANE]: 16,
    },
    /**
     * Caps how many jobs run at once inside one lane of a family, never across the family.
     *
     * @remarks
     * Two accounts per chain, one query per exchange location, one removal per chain. Read a value
     * as "per chain" or "per location", not as a budget the whole family shares.
     */
    laneFamilies: { [ACCOUNT_SYNC_LANE_PREFIX]: 2, [ACCOUNTS_ADD_LANE_PREFIX]: 2, [ACCOUNTS_REMOVE_LANE_PREFIX]: 1, [DETECT_LANE_PREFIX]: 2, [EXCHANGE_EVENTS_LANE_PREFIX]: 1 },
    /**
     * Caps how many lanes of a family are live at once, which {@link laneFamilies} does not do.
     *
     * @remarks
     * Every chain's accounts are declared up front, so the per-lane cap alone would let all chains
     * progress together. Detection's entry must not exceed the balances cap: a chain only detects
     * inside its own chain job, so a further active detect lane is one nothing can fill.
     */
    laneFamilyActive: { [ACCOUNT_SYNC_LANE_PREFIX]: 2, [ACCOUNTS_ADD_LANE_PREFIX]: 2, [ACCOUNTS_REMOVE_LANE_PREFIX]: 1, [DETECT_LANE_PREFIX]: 2, [EXCHANGE_EVENTS_LANE_PREFIX]: 2 },
  });
  const activities = shallowRef<Activity[]>([]);
  /**
   * The reactivity handle for the orchestrator's non-reactive records and ledger.
   *
   * @remarks
   * Bumped on every change, which is what makes a `useWorkStatus` computed re-read them. A ledger
   * write always co-occurs with an emit, so this captures freshness as well as liveness.
   */
  const version = shallowRef<number>(0);

  orchestrator.onChange(() => {
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
