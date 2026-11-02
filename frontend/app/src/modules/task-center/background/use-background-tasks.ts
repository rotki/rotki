import { startPromise } from '@shared/utils';
import { err, ok, type Result } from 'plainfp/result';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { BackendCancelled, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { BACKGROUND_LANE, Priority } from '@/modules/task-center/core/orchestrator/spec';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import {
  type BackgroundTask,
  BackgroundTaskKind,
  backgroundTaskKindOf,
  BackgroundTaskStatus,
  type BackgroundTaskStatusData,
} from './background-task-types';
import { backgroundTaskActivity, backgroundTaskLabel, backgroundTaskTitle } from './background-task.activity';

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
}

/**
 * Mirrors the backend task manager's tasks as dock rows.
 *
 * @remarks
 * Each task becomes an activity whose run waits for the task's end message, so the orchestrator
 * owns the row's lifecycle like any other: it settles on logout with the rest of the session's
 * work, which matters because the backend sends nothing while it stops its tasks.
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

  const mirrors = new Map<number, Mirror>();

  function mirror(task: BackgroundTask, settled?: MirrorOutcome): void {
    if (mirrors.has(task.id))
      return;

    let finish: (outcome: MirrorOutcome) => void = () => {};
    const outcome = new Promise<MirrorOutcome>((resolve) => {
      finish = resolve;
    });
    if (settled === undefined)
      mirrors.set(task.id, { finish, since: Date.now() });
    else
      finish(settled);

    startPromise((async (): Promise<void> => {
      await submitTask({
        id: backgroundTaskActivity.id(task),
        interruptible: false,
        kind: backgroundTaskActivity.kind,
        lane: BACKGROUND_LANE,
        priority: Priority.BACKGROUND,
        run: async () => outcome,
        subtitle: backgroundTaskLabel(task, getChainName),
        title: t(backgroundTaskTitle(task)),
      });
      mirrors.delete(task.id);
    })());
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

  return { onStatus, resync };
});
