import type { ComputedRef, Ref } from 'vue';
import { map as mapResult, match, type Result } from 'plainfp/result';
import { logger } from '@/modules/core/common/logging/logging';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { activityLabel } from '@/modules/task-center/activity-labels';
import { ActivityKind, type ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

/** What every staking query reports besides its positions. */
interface StakingResponse {
  /** The addresses whose positions could not be queried. */
  failed: string[];
}

interface FetchedStaking<TRow> {
  failed: string[];
  rows: TRow[];
}

interface UseStakingRowsOptions<TResponse extends StakingResponse, TRow, TTotal> {
  /** Which staking activity this query reports as in the task center. */
  part: ActivityPart;
  /** Starts the backend query for the positions of every tracked account, which runs as a task. */
  query: () => Promise<{ taskId: number }>;
  /** Validates the task result. */
  parse: (result: unknown) => TResponse;
  /** Flattens the response into table rows. */
  toRows: (response: TResponse) => TRow[];
  /** Aggregates the rows into the figure shown above the table. */
  toTotal: (rows: TRow[]) => TTotal;
}

export interface UseStakingRowsReturn<TRow, TTotal> {
  /** The addresses the last successful query could not load. */
  failedAddresses: ComputedRef<string[]>;
  /**
   * Whether a query has succeeded yet. Until one has, empty rows mean nothing is known rather than
   * that there are no positions, so a table must not say there are none.
   */
  loaded: Readonly<Ref<boolean>>;
  loading: Readonly<Ref<boolean>>;
  refresh: () => Promise<void>;
  rows: ComputedRef<TRow[]>;
  total: ComputedRef<TTotal>;
}

/**
 * Loads the staking positions of a chain and exposes them as table rows with a total.
 *
 * @remarks
 * The query runs as a task, so a failure is reported by its row in the task center and the rows
 * of the last successful query stay on screen. The rows are taken from the task's outcome rather
 * than written inside it, because a submit that joins a run already in flight never runs its own
 * body, yet still receives that run's outcome.
 */
export function useStakingRows<TResponse extends StakingResponse, TRow, TTotal>(
  { parse, part, query, toRows, toTotal }: UseStakingRowsOptions<TResponse, TRow, TTotal>,
): UseStakingRowsReturn<TRow, TTotal> {
  const { t } = useI18n({ useScope: 'global' });
  const { submitTask } = useNativeTask();

  const rows = shallowRef<TRow[]>([]);
  const failedAddresses = shallowRef<string[]>([]);
  const loaded = shallowRef<boolean>(false);
  const loading = shallowRef<boolean>(false);

  const total = computed<TTotal>(() => toTotal(get(rows)));

  async function refresh(): Promise<void> {
    set(loading, true);
    try {
      const outcome = await submitTask({
        id: makeActivityId(ActivityKind.STAKING, part),
        kind: ActivityKind.STAKING,
        rerunnable: true,
        run: async ({ runTask }): Promise<Result<FetchedStaking<TRow>, TaskError>> => mapResult(
          await runTask<unknown>(async () => query()),
          (result) => {
            const response = parse(result);
            return { failed: response.failed, rows: toRows(response) };
          },
        ),
        subtitle: activityLabel(ActivityKind.STAKING, part),
        title: t('task_center.group.staking'),
      });

      match(outcome, {
        err: () => {},
        ok: (fetched) => {
          set(rows, fetched.rows);
          set(failedAddresses, fetched.failed);
          set(loaded, true);
        },
      });
      onActionableError(outcome, error => logger.error(`action failure for ${part} staking:`, error));
    }
    finally {
      set(loading, false);
    }
  }

  return {
    failedAddresses: computed<string[]>(() => get(failedAddresses)),
    loaded: readonly(loaded),
    loading: readonly(loading),
    refresh,
    rows: computed<TRow[]>(() => get(rows)),
    total,
  };
}
