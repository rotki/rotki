import type { ComputedRef } from 'vue';
import { assembleActivityModel } from './core/model';
import {
  type Activity,
  ActivityKind,
  type ActivityModel,
  type ActivityOverall,
  ActivityPhase,
  type TranslateFn,
  type WorkStatus,
} from './core/types';
import { useTaskOrchestrator } from './use-task-orchestrator';

// Re-exported so consumers can pull the composable and the kind enum from one module.
export { ActivityKind };

interface UseTaskCenterReturn {
  model: ComputedRef<ActivityModel>;
  active: ComputedRef<Activity[]>;
  pending: ComputedRef<Activity[]>;
  current: ComputedRef<Activity | undefined>;
  overall: ComputedRef<ActivityOverall>;
  isActive: ComputedRef<boolean>;
  /** Reactive liveness + freshness for a kind (or specific id) — replaces `useSectionStatus`. */
  useWorkStatus: (kind: ActivityKind, ...parts: (string | number)[]) => ComputedRef<WorkStatus>;
  /**
   * Reactive liveness + freshness aggregated over every activity whose id extends `kind:parts` —
   * the coarse read for producers that submit one activity per request.
   */
  useWorkStatusPrefix: (kind: ActivityKind, ...parts: (string | number)[]) => ComputedRef<WorkStatus>;
  /** Liveness only — see `useIsActive` on the orchestrator shell. */
  useIsActive: (kind: ActivityKind, ...parts: (string | number)[]) => ComputedRef<boolean>;
  /** Liveness only, aggregated over a prefix. */
  useIsActivePrefix: (kind: ActivityKind, ...parts: (string | number)[]) => ComputedRef<boolean>;
  /** Reactive live {@link Activity} for a kind (or specific id) — the native progress channel. */
  useActivity: (kind: ActivityKind, ...parts: (string | number)[]) => ComputedRef<Activity | undefined>;
}

/**
 * Reactive shell over the read model: assembles the orchestrator's activities into one
 * {@link ActivityModel}. All logic lives in the pure core; this file is wiring + the injected
 * translator that keeps the core free of `useI18n`.
 */
export const useTaskCenter = createSharedComposable((): UseTaskCenterReturn => {
  const { t } = useI18n({ useScope: 'global' });
  const translate: TranslateFn = (key, params) => (params ? t(key, params) : t(key));

  const { activities, useActivity, useIsActive, useIsActivePrefix, useWorkStatus, useWorkStatusPrefix } = useTaskOrchestrator();

  const model = computed<ActivityModel>(() => assembleActivityModel(get(activities), translate));

  const active = computed<Activity[]>(() => get(model).active);
  const pending = computed<Activity[]>(() => get(model).pending);
  const current = computed<Activity | undefined>(() => get(model).current);
  const overall = computed<ActivityOverall>(() => get(model).overall);
  const isActive = computed<boolean>(() => get(model).overall.phase === ActivityPhase.WORKING);

  return { active, current, isActive, model, overall, pending, useActivity, useIsActive, useIsActivePrefix, useWorkStatus, useWorkStatusPrefix };
});
