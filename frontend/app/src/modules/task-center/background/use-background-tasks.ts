import { startPromise } from '@shared/utils';
import { createSharedComposable } from '@vueuse/core';
import { err, ok, type Result } from 'plainfp/result';
import { useI18n } from 'vue-i18n';
import { type MessageKey, msg } from '@/message-key';
import { FailureCause, parseFailureCause } from '@/modules/core/api/failure-cause';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { onSessionCleared } from '@/modules/core/session/session-lifecycle';
import { BackendCancelled, Skipped, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { BACKGROUND_LANE, Priority } from '@/modules/task-center/core/orchestrator/spec';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';
import {
  type BackgroundTask,
  BackgroundTaskKind,
  backgroundTaskKindOf,
  BackgroundTaskStatus,
  type BackgroundTaskStatusData,
  type CostBasisStalled,
} from './background-task-types';
import { backgroundTaskActivity, backgroundTaskLabel, backgroundTaskTitle, costBasisStalledActivity } from './background-task.activity';

const STALLED_REASON_KEYS: Partial<Record<FailureCause, MessageKey>> = {
  [FailureCause.NETWORK]: msg.$t('task_center.cost_basis_stalled.network'),
  [FailureCause.RATE_LIMITED]: msg.$t('task_center.cost_basis_stalled.rate_limited'),
};

type MirrorOutcome = Result<void, TaskError>;

interface Mirror {
  /** Settles the mirror's run with the task's outcome. */
  readonly finish: (outcome: MirrorOutcome) => void;
  /** When the mirror was created, in milliseconds, to tell it apart from a periodic read sent before it. */
  readonly since: number;
}

interface UseBackgroundTasksReturn {
  /** Apply one `background_task_status` message. */
  onStatus: (data: BackgroundTaskStatusData) => void;
  /**
   * Match the mirrors to the tasks the periodic data says are running.
   *
   * @remarks
   * `requestedAt` is when the periodic request was sent, in milliseconds. A mirror created after it
   * may be missing from the list only because the read predates it, so it is left alone.
   */
  resync: (running: readonly BackgroundTask[], requestedAt: number) => void;
  /**
   * Surface a persisted cost-basis stall as an attention-flagged background row, or clear it once
   * processing catches up.
   *
   * @remarks
   * Keyed on `(since, reason)` so repeated periodic polls neither duplicate nor re-open a row the
   * user already dismissed, while a new stall (`since`) supersedes the earlier row.
   */
  syncCostBasisStalled: (stalled: CostBasisStalled | undefined) => void;
}

/**
 * Mirrors the backend task manager's tasks as dock rows.
 *
 * @remarks
 * Each task becomes an activity whose run waits for the task's end message, so the orchestrator
 * owns the row's lifecycle like any other: it settles on logout with the rest of the session's
 * work, which matters because the backend sends nothing while it stops its tasks. A run that ends
 * without failing is forgotten as it settles, since nothing reports it and the task manager starts
 * new runs all session.
 *
 * Start and end messages are dropped when no client is connected, so the periodic data fills the
 * gaps: a running task with no row gets one, and a row whose task is gone settles complete. Its
 * real outcome is unknown, but a failure that the user should see is held by the backend and
 * arrives as its own message.
 *
 * A task of {@link BackgroundTaskKind.OTHER} is upkeep the user has no reason to watch, so it gets a
 * row only once it fails with an error.
 */
export const useBackgroundTasks = createSharedComposable((): UseBackgroundTasksReturn => {
  const { t } = useI18n({ useScope: 'global' });
  const { getChainName } = useSupportedChains();
  const { submitTask } = useNativeTask();
  const { forget } = useTaskOrchestrator();

  const mirrors = new Map<number, Mirror>();
  let lastStalled: CostBasisStalled | undefined;

  onSessionCleared('background-tasks-stalled', () => {
    lastStalled = undefined;
  });

  function mirror(task: BackgroundTask, settled?: MirrorOutcome): void {
    if (mirrors.has(task.id))
      return;

    let resolve: (outcome: MirrorOutcome) => void = () => {};
    const outcome = new Promise<MirrorOutcome>((resolver) => {
      resolve = resolver;
    });
    const entry: Mirror = {
      finish: (result) => {
        dropMirror(task.id, entry);
        resolve(result);
      },
      since: Date.now(),
    };
    if (settled === undefined)
      mirrors.set(task.id, entry);
    else
      resolve(settled);

    startPromise((async (): Promise<void> => {
      await submitTask({
        forgetUnlessFailed: true,
        id: backgroundTaskActivity.id(task),
        interruptible: false,
        kind: backgroundTaskActivity.kind,
        lane: BACKGROUND_LANE,
        priority: Priority.BACKGROUND,
        run: async () => outcome,
        subtitle: backgroundTaskLabel(task, getChainName),
        title: t(backgroundTaskTitle(task)),
      });
      dropMirror(task.id, entry);
    })());
  }

  /**
   * Drops a settled mirror at once, so a failure that arrives right after a resync settled its row
   * starts a failed row instead of settling the already settled one. Only drops this entry, never a
   * later mirror of the same task.
   */
  function dropMirror(id: number, entry: Mirror): void {
    if (mirrors.get(id) === entry)
      mirrors.delete(id);
  }

  function failureOf(error: string): MirrorOutcome {
    return err(TaskFailed({ message: error }));
  }

  /**
   * The outcome a task's end message settles its row with. A failure the backend does not treat as
   * an error carries no `error` and settles complete, since nothing is wrong for the user to see.
   */
  function outcomeOf({ error, status }: BackgroundTaskStatusData): MirrorOutcome {
    if (status === BackgroundTaskStatus.CANCELLED)
      return err(BackendCancelled({ message: 'cancelled by the backend' }));
    return error === undefined ? ok(undefined) : failureOf(error);
  }

  function onStatus(data: BackgroundTaskStatusData): void {
    const { error, status } = data;
    if (status === BackgroundTaskStatus.STARTED) {
      if (backgroundTaskKindOf(data.kind) !== BackgroundTaskKind.OTHER)
        mirror(data);
      return;
    }

    const running = mirrors.get(data.id);
    if (running)
      running.finish(outcomeOf(data));
    else if (error !== undefined)
      mirror(data, failureOf(error));
  }

  function resync(running: readonly BackgroundTask[], requestedAt: number): void {
    const runningIds = new Set<number>(running.map(task => task.id));
    for (const [id, { finish, since }] of mirrors) {
      if (!runningIds.has(id) && since < requestedAt)
        finish(ok(undefined));
    }

    for (const task of running) {
      if (backgroundTaskKindOf(task.kind) !== BackgroundTaskKind.OTHER)
        mirror(task);
    }
  }

  function syncCostBasisStalled(stalled: CostBasisStalled | undefined): void {
    if (stalled === undefined) {
      if (lastStalled !== undefined) {
        forget(costBasisStalledActivity.id(lastStalled.since));
        lastStalled = undefined;
      }
      return;
    }

    if (lastStalled?.since === stalled.since && lastStalled.reason === stalled.reason)
      return;

    lastStalled = stalled;
    const id = costBasisStalledActivity.id(stalled.since);
    const cause = parseFailureCause(stalled.reason);
    const message = t(STALLED_REASON_KEYS[cause] ?? msg.$t('task_center.cost_basis_stalled.unknown'));

    startPromise((async (): Promise<void> => {
      await submitTask({
        forgetUnlessFailed: true,
        id,
        interruptible: false,
        kind: costBasisStalledActivity.kind,
        lane: BACKGROUND_LANE,
        priority: Priority.BACKGROUND,
        run: async () => err(Skipped({ attention: true, message })),
        subtitle: activityLabelFor(msg.$t('task_center.activity.background_task.historical_balances')),
        title: t(msg.$t('task_center.background_task.historical_balances')),
      });
      if (lastStalled === undefined || costBasisStalledActivity.id(lastStalled.since) !== id)
        forget(id);
    })());
  }

  return { onStatus, resync, syncCostBasisStalled };
});
