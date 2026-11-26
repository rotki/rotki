import type { ActivityDescriptor } from '@/modules/task-center/core/activity-descriptor';
import { logicOr } from '@vueuse/math';
import { set } from '@vueuse/shared';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { type ComputedRef, type MaybeRefOrGetter, type Ref, ref, type ShallowRef, shallowRef, toValue } from 'vue';
import { useI18n } from 'vue-i18n';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { logger } from '@/modules/core/common/logging/logging';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { useHistoryStore } from '@/modules/history/use-history-store';
import { activityLabelOf } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseAutoMatchingTaskOptions {
  /** The matching activity the run is submitted as, and whose liveness counts as loading. */
  activity: ActivityDescriptor<void, readonly []>;
  /** Whether the user's tier may run the matching; a run is skipped when it may not. */
  allowed: MaybeRefOrGetter<boolean>;
  /**
   * Set while a run this composable started is in flight. Module-level in the caller, so the
   * state outlives a `createSharedComposable` teardown.
   */
  loading: Ref<boolean>;
  /** Starts the backend matching task. */
  trigger: () => Promise<{ taskId: number }>;
  /** Re-reads the unmatched list after a successful run, before the events are signalled as modified. */
  onMatched: () => Promise<void>;
  /** Logged with an actionable failure of the run. */
  failureLog: string;
}

interface UseAutoMatchingTaskReturn {
  /** A run this composable started, or any run of the activity, is in flight. */
  autoMatchLoading: ComputedRef<boolean>;
  /** Submits the matching run, unless it is not allowed or one is already active. */
  triggerAutoMatching: () => Promise<void>;
}

/** Runs a backend auto-matching task through the task center and refreshes what it changed. */
export function useAutoMatchingTask(options: UseAutoMatchingTaskOptions): UseAutoMatchingTaskReturn {
  const { activity, allowed, failureLog, loading, onMatched, trigger } = options;
  const { t } = useI18n({ useScope: 'global' });
  const { statusOf, submitTask } = useNativeTask();
  const { useIsActive } = useTaskCenter();
  const { signalEventsModified } = useHistoryStore();

  const autoMatchLoading = logicOr(loading, useIsActive(activity.kind, ...activity.partsOf()));

  const triggerAutoMatching = async (): Promise<void> => {
    if (!toValue(allowed) || statusOf(activity.kind, ...activity.partsOf()).active)
      return;

    set(loading, true);

    const outcome = await submitTask({
      id: activity.id(),
      kind: activity.kind,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<boolean>(
          async () => trigger(),
        ),
        () => {},
      ),
      subtitle: activityLabelOf(activity),
      title: t('task_center.group.history_events'),
    });

    if (!isErr(outcome)) {
      await onMatched();
      signalEventsModified();
    }
    else if (isActionable(outcome.error)) {
      logger.error(failureLog, outcome.error);
    }

    set(loading, false);
  };

  return { autoMatchLoading, triggerAutoMatching };
}

interface UnmatchedLists<T> {
  unmatched: Ref<T[]>;
  ignored: Ref<T[]>;
  loading: Ref<boolean>;
  ignoredLoading: Ref<boolean>;
  /** Why the last fetch of the unmatched items failed, kept until a load succeeds. */
  unmatchedError: ShallowRef<unknown>;
  /** Why the last fetch of the ignored items failed, kept until a load succeeds. */
  ignoredError: ShallowRef<unknown>;
  /**
   * Loads the unmatched, or with `onlyIgnored` the ignored, items through `fetcher`.
   *
   * @remarks
   * A websocket message triggers this in the background as well, so a failure is kept for the list
   * to show rather than interrupting the user with a dialog. The rows of the last good load stay,
   * since the action center counts them, and the failure is kept until a load succeeds. A
   * cancelled request changes neither.
   */
  load: (onlyIgnored: boolean | undefined, fetcher: () => Promise<T[]>, failureLog: string) => Promise<void>;
}

/**
 * The module-level state of one unmatched/ignored pair of lists, and its load bookkeeping.
 *
 * @remarks
 * Called at module top level, so the lists outlive a `createSharedComposable` teardown. The lists
 * are deep refs so readers keep getting reactive items; `ref` types a generic `T` as
 * `UnwrapRef<T>`, which TypeScript cannot relate back to `T`, hence the assertions.
 */
export function createUnmatchedLists<T>(): UnmatchedLists<T> {
  // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- the items are plain data with no nested refs, so UnwrapRef<T> is T
  const unmatched = ref<T[]>([]) as Ref<T[]>;
  // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- as above
  const ignored = ref<T[]>([]) as Ref<T[]>;
  const loading = ref<boolean>(false);
  const ignoredLoading = ref<boolean>(false);
  const unmatchedError = shallowRef<unknown>();
  const ignoredError = shallowRef<unknown>();

  const load = async (onlyIgnored: boolean | undefined, fetcher: () => Promise<T[]>, failureLog: string): Promise<void> => {
    const isIgnored = onlyIgnored === true;
    const loadingRef = isIgnored ? ignoredLoading : loading;
    const itemsRef = isIgnored ? ignored : unmatched;
    const errorRef = isIgnored ? ignoredError : unmatchedError;

    set(loadingRef, true);
    try {
      set(itemsRef, await fetcher());
      set(errorRef, undefined);
    }
    catch (error: unknown) {
      if (isRequestCancellation(error))
        return;
      logger.error(failureLog, error);
      set(errorRef, error);
    }
    finally {
      set(loadingRef, false);
    }
  };

  return { ignored, ignoredError, ignoredLoading, load, loading, unmatched, unmatchedError };
}
