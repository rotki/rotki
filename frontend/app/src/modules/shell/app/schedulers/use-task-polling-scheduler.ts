import { startPromise } from '@shared/utils';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { useTaskMonitor } from '@/modules/core/tasks/use-task-monitor';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';

/**
 * How often to look for results while backend tasks are outstanding.
 *
 * A task's latency is bounded below by this interval: the backend can finish in milliseconds, but
 * nothing observes it until the next poll. Combined with a capped lane that only releases a slot
 * once the previous task is seen to finish, the interval sets the pace of the whole queue —
 * measured on a login balance refresh, 26 per-chain calls of ~20ms each took 210 seconds, arriving
 * in pairs exactly one interval apart.
 */
const ACTIVE_POLLING_MS = 500;

/**
 * How often to look while nothing is outstanding.
 *
 * Only a safety net for tasks this client did not start — a task submitted here schedules a poll
 * itself. Kept at the previous fixed interval so an idle session is no busier than before.
 */
const IDLE_POLLING_MS = 4_000;

/**
 * How much to slow down after each poll that changed nothing.
 *
 * Polling fast is only worth it while an answer might arrive: most tasks finish in milliseconds, so
 * the first look after work starts is the one that pays. A task that has already been running for
 * ten seconds is not going to be observed meaningfully sooner by asking eight times a second, so
 * the interval decays 500ms · 750 · 1.1s · 1.7s · 2.5s toward the idle rate, and snaps back to
 * {@link ACTIVE_POLLING_MS} the moment the set of outstanding tasks changes.
 */
const BACKOFF_FACTOR = 1.5;

interface UseTaskPollingSchedulerReturn {
  start: (immediate: boolean) => void;
  stop: () => void;
}

/**
 * Poll for task results, quickly when something has just changed and progressively slower while it
 * has not.
 *
 * Self-rescheduling rather than `setInterval`, for two reasons: the delay has to be chosen from the
 * state at each tick, and the next poll must not be scheduled until the previous one has finished —
 * a fixed interval lets a slow monitor pass overlap the next one and query the same tasks twice.
 */
export function useTaskPollingScheduler(): UseTaskPollingSchedulerReturn {
  const { monitor } = useTaskMonitor();
  const { hasRunningTasks, hasUnknownTasks, tasks } = storeToRefs(useTaskStore());
  const { connected } = storeToRefs(useMainStore());

  let timeoutId: NodeJS.Timeout | undefined;
  let running = false;
  let activeDelay = ACTIVE_POLLING_MS;
  let lastSeen = '';

  /**
   * Which tasks are outstanding right now. Compared between polls so that a task starting or
   * finishing resets the pace: either is a sign that more is about to happen.
   */
  function outstanding(): string {
    return Object.keys(get(tasks)).join(',');
  }

  function nextDelay(): number {
    if (!get(hasRunningTasks) && !get(hasUnknownTasks)) {
      activeDelay = ACTIVE_POLLING_MS;
      lastSeen = '';
      return IDLE_POLLING_MS;
    }

    const current = outstanding();
    if (current !== lastSeen) {
      lastSeen = current;
      activeDelay = ACTIVE_POLLING_MS;
    }
    else {
      activeDelay = Math.min(activeDelay * BACKOFF_FACTOR, IDLE_POLLING_MS);
    }

    return activeDelay;
  }

  function schedule(): void {
    if (!running)
      return;

    timeoutId = setTimeout(() => startPromise(tick()), nextDelay());
  }

  async function tick(): Promise<void> {
    try {
      // Skip the pass while the backend is deliberately down — a restart in
      // flight, or a backend being switched. It cannot answer, so polling it
      // only fills the console with failed requests for the whole window (a
      // core restart takes seconds, and the active pace is twice a second).
      // Skipping rather than stopping means polling resumes on its own when the
      // connection returns, with no one having to restart the scheduler.
      if (get(connected))
        await monitor();
    }
    finally {
      // Rescheduled even when the pass throws, or one failed poll ends polling for the session.
      schedule();
    }
  }

  function start(immediate: boolean): void {
    if (running)
      return;

    running = true;
    if (immediate)
      startPromise(tick());
    else
      schedule();
  }

  function stop(): void {
    running = false;
    if (timeoutId) {
      clearTimeout(timeoutId);
      timeoutId = undefined;
    }
  }

  onScopeDispose(stop);

  return { start, stop };
}
