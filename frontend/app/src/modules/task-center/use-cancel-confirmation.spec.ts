import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  type Activity,
  ActivityKind,
  ActivitySourceType,
  ActivityStatus,
  makeActivityId,
} from './core/types';
import { useCancelConfirmation } from './use-cancel-confirmation';

const activities = ref<Activity[]>([]);
const cancel = vi.fn();
const dismiss = vi.fn();
const show = vi.fn();

vi.mock('./use-task-orchestrator', () => ({
  useTaskOrchestrator: (): { activities: Ref<Activity[]> } => ({ activities }),
}));

vi.mock('./use-task-controller', () => ({
  useTaskController: (): { cancel: (activity: Activity) => Promise<void> } => ({ cancel }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): { dismiss: () => void; show: typeof show } => ({ dismiss, show }),
}));

function activity(status: ActivityStatus, subtitle?: string): Activity {
  return {
    cancellable: true,
    id: makeActivityId(ActivityKind.TX_SYNC, 'ethereum'),
    kind: ActivityKind.TX_SYNC,
    percentage: -1,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    status,
    subtitle,
    title: 'Transaction sync',
  };
}

describe('useCancelConfirmation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(activities, [activity(ActivityStatus.RUNNING)]);
  });

  /** Closes the dialog the way a user backing out would, so its watcher does not outlive the test. */
  function dismissDialog(): void {
    const call = show.mock.calls.at(-1);
    assert(call, 'no confirmation was shown');
    call[2]();
  }

  it('should name the activity in the prompt, preferring its subtitle', () => {
    useCancelConfirmation().confirmCancel(activity(ActivityStatus.RUNNING, 'Ethereum'));

    expect(show).toHaveBeenCalledWith(
      expect.objectContaining({ message: 'collapsed_pending_tasks.cancel_task_info::Ethereum' }),
      expect.any(Function),
      expect.any(Function),
    );
    dismissDialog();
  });

  it('should fall back to the title when there is no subtitle', () => {
    useCancelConfirmation().confirmCancel(activity(ActivityStatus.RUNNING));

    expect(show).toHaveBeenCalledWith(
      expect.objectContaining({ message: 'collapsed_pending_tasks.cancel_task_info::Transaction sync' }),
      expect.any(Function),
      expect.any(Function),
    );
    dismissDialog();
  });

  it('should cancel the activity when the user confirms', async () => {
    const target = activity(ActivityStatus.RUNNING);
    useCancelConfirmation().confirmCancel(target);

    await show.mock.calls[0][1]();

    expect(cancel).toHaveBeenCalledWith(target);
  });

  it('should cancel nothing when the user backs out', () => {
    useCancelConfirmation().confirmCancel(activity(ActivityStatus.RUNNING));

    show.mock.calls[0][2]();

    expect(cancel).not.toHaveBeenCalled();
  });

  /**
   * The dialog names one activity, and work settles on its own schedule. Left up, it asks the user
   * to confirm cancelling something already finished — and confirming would cancel nothing, since
   * the orchestrator refuses a terminal id.
   */
  it('should dismiss itself when the work settles first', async () => {
    vi.useFakeTimers();
    useCancelConfirmation().confirmCancel(activity(ActivityStatus.RUNNING));

    set(activities, [activity(ActivityStatus.COMPLETE)]);
    await nextTick();
    await vi.advanceTimersByTimeAsync(1000);

    expect(dismiss).toHaveBeenCalledOnce();
    vi.useRealTimers();
  });

  /**
   * The watcher belongs to no component scope, so one that outlives its dialog is never collected.
   * Before the self-dismiss stopped it, it went on firing for the life of the session and closed
   * whatever confirmation happened to be open at the next settle.
   */
  it('should stop watching once it has dismissed itself', async () => {
    vi.useFakeTimers();
    useCancelConfirmation().confirmCancel(activity(ActivityStatus.RUNNING));

    set(activities, [activity(ActivityStatus.COMPLETE)]);
    await nextTick();
    await vi.advanceTimersByTimeAsync(1000);
    dismiss.mockClear();

    set(activities, [activity(ActivityStatus.RUNNING)]);
    await nextTick();
    set(activities, [activity(ActivityStatus.CANCELLED)]);
    await nextTick();
    await vi.advanceTimersByTimeAsync(1000);

    expect(dismiss).not.toHaveBeenCalled();
    vi.useRealTimers();
  });

  /**
   * Unwatching does not unschedule a debounce that is already pending. The settle arms the 1s
   * self-dismiss, the user backs out inside that second, and the timer still fires — dismissing
   * whatever confirmation is open by then rather than the one it was armed for.
   */
  it('should not dismiss anything when the user backs out inside the debounce window', async () => {
    vi.useFakeTimers();
    useCancelConfirmation().confirmCancel(activity(ActivityStatus.RUNNING));

    set(activities, [activity(ActivityStatus.COMPLETE)]);
    await nextTick();
    await vi.advanceTimersByTimeAsync(500);

    dismissDialog();
    await vi.advanceTimersByTimeAsync(1000);

    expect(dismiss).not.toHaveBeenCalled();
    vi.useRealTimers();
  });

  it('should not dismiss anything when the user confirms inside the debounce window', async () => {
    vi.useFakeTimers();
    useCancelConfirmation().confirmCancel(activity(ActivityStatus.RUNNING));

    set(activities, [activity(ActivityStatus.COMPLETE)]);
    await nextTick();
    await vi.advanceTimersByTimeAsync(500);

    await show.mock.calls[0][1]();
    await vi.advanceTimersByTimeAsync(1000);

    expect(dismiss).not.toHaveBeenCalled();
    vi.useRealTimers();
  });

  it('should stay up while the work is still running', async () => {
    vi.useFakeTimers();
    useCancelConfirmation().confirmCancel(activity(ActivityStatus.RUNNING));

    set(activities, [activity(ActivityStatus.RUNNING), activity(ActivityStatus.PENDING)]);
    await nextTick();
    await vi.advanceTimersByTimeAsync(1000);

    expect(dismiss).not.toHaveBeenCalled();
    vi.useRealTimers();
  });
});
