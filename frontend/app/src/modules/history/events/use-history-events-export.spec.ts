import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import { Severity } from '@rotki/common';
import { err, ok, type Result } from 'plainfp/result';
import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { computed, type ComputedRef } from 'vue';
import { Cancelled, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useHistoryEventsExport } from '@/modules/history/events/use-history-events-export';

const { confirm, downloadHistoryEventsCSV, exportHistoryEventsCSV, interop, notify, submitTask } = vi.hoisted(() => {
  /** Holds the callback the confirmation store was handed, so a test can accept the prompt. */
  const confirm: { run?: () => Promise<void> } = {};

  return {
    confirm,
    downloadHistoryEventsCSV: vi.fn(async () => {}),
    exportHistoryEventsCSV: vi.fn(),
    interop: { appSession: false, openDirectory: vi.fn() },
    notify: vi.fn(),
    submitTask: vi.fn(),
  };
});

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): typeof interop => interop,
}));

vi.mock('@/modules/history/api/events/use-history-events-api', () => ({
  useHistoryEventsApi: (): Record<string, Mock> => ({ downloadHistoryEventsCSV, exportHistoryEventsCSV }),
}));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: (): { submitTask: Mock } => ({ submitTask }),
}));

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): { useIsActive: () => ComputedRef<boolean> } => ({
    useIsActive: () => computed(() => true),
  }),
}));

vi.mock('@/modules/core/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: (): { notify: Mock } => ({ notify }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): { show: (message: unknown, run: () => Promise<void>) => void } => ({
    show: (_message, run): void => {
      confirm.run = run;
    },
  }),
}));

const filters: HistoryEventRequestPayload = {
  aggregateByGroupIds: true,
  limit: 10,
  location: 'ethereum',
  offset: 20,
};

function taskFailed(message: string): TaskError {
  return TaskFailed({ message });
}

/** Runs the export the way the user does: press the control, then accept the confirmation. */
async function exportAfterConfirming(matchExactEvents = false): Promise<void> {
  const { showConfirmation } = useHistoryEventsExport(() => filters, () => matchExactEvents);
  showConfirmation();
  await confirm.run?.();
}

/** Invokes the task body the export handed the task centre, with a stand-in `runTask`. */
async function runSubmittedTask(result: Result<boolean | { filePath: string }, TaskError>): Promise<void> {
  const spec = submitTask.mock.calls[0][0];
  await spec.run({ runTask: async (fn: () => Promise<unknown>) => {
    await fn();
    return result;
  } });
}

describe('useHistoryEventsExport', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    confirm.run = undefined;
    interop.appSession = false;
    interop.openDirectory.mockResolvedValue('/tmp/export');
    exportHistoryEventsCSV.mockResolvedValue(true);
    submitTask.mockResolvedValue(ok(true));
  });

  it('should report the export as running while the task centre says so', () => {
    const { taskRunning } = useHistoryEventsExport(() => filters, () => false);

    expect(get(taskRunning)).toBe(true);
  });

  it('should not export until the confirmation is accepted', () => {
    const { showConfirmation } = useHistoryEventsExport(() => filters, () => false);

    showConfirmation();

    expect(submitTask).not.toHaveBeenCalled();
  });

  describe('choosing where the file goes', () => {
    it('should ask the app session for a directory', async () => {
      interop.appSession = true;

      await exportAfterConfirming();

      expect(interop.openDirectory).toHaveBeenCalledTimes(1);
      expect(submitTask).toHaveBeenCalledTimes(1);
    });

    it('should abandon the export when the directory picker is dismissed', async () => {
      interop.appSession = true;
      interop.openDirectory.mockResolvedValue(undefined);

      await exportAfterConfirming();

      expect(submitTask).not.toHaveBeenCalled();
      expect(notify).not.toHaveBeenCalled();
    });

    it('should not ask a browser session where to put it', async () => {
      await exportAfterConfirming();

      expect(interop.openDirectory).not.toHaveBeenCalled();
      expect(submitTask).toHaveBeenCalledTimes(1);
    });
  });

  /** The export covers everything the filters match, so the table's paging must not narrow it. */
  describe('what the backend is asked for', () => {
    it('should drop the paging and grouping the table was using', async () => {
      await exportAfterConfirming();
      await runSubmittedTask(ok(true));

      expect(exportHistoryEventsCSV).toHaveBeenCalledWith({
        location: 'ethereum',
        matchExactEvents: false,
      }, undefined);
    });

    it('should pass on whether the matched events were asked for', async () => {
      await exportAfterConfirming(true);
      await runSubmittedTask(ok(true));

      expect(exportHistoryEventsCSV).toHaveBeenCalledWith(
        expect.objectContaining({ matchExactEvents: true }),
        undefined,
      );
    });

    it('should send the directory the app session chose', async () => {
      interop.appSession = true;

      await exportAfterConfirming();
      await runSubmittedTask(ok(true));

      expect(exportHistoryEventsCSV).toHaveBeenCalledWith(expect.anything(), '/tmp/export');
    });
  });

  describe('reporting the outcome in an app session', () => {
    beforeEach(() => {
      interop.appSession = true;
    });

    it('should confirm the file was written', async () => {
      await exportAfterConfirming();

      expect(notify).toHaveBeenCalledWith(expect.objectContaining({
        message: 'actions.history_events_export.message.success',
        severity: Severity.INFO,
      }));
    });

    it('should report a backend that declined to write one', async () => {
      submitTask.mockResolvedValue(ok(false));

      await exportAfterConfirming();

      expect(notify).toHaveBeenCalledWith(expect.objectContaining({ severity: Severity.ERROR }));
    });
  });

  describe('reporting the outcome in a browser session', () => {
    it('should stream the generated file back instead of announcing it', async () => {
      submitTask.mockResolvedValue(ok({ filePath: '/tmp/events.csv' }));

      await exportAfterConfirming();

      expect(downloadHistoryEventsCSV).toHaveBeenCalledWith('/tmp/events.csv');
      expect(notify).not.toHaveBeenCalled();
    });

    it('should still report a failure', async () => {
      submitTask.mockResolvedValue(ok(false));

      await exportAfterConfirming();

      expect(downloadHistoryEventsCSV).not.toHaveBeenCalled();
      expect(notify).toHaveBeenCalledWith(expect.objectContaining({ severity: Severity.ERROR }));
    });
  });

  describe('when the task fails', () => {
    it('should surface an actionable failure with what the task said', async () => {
      submitTask.mockResolvedValue(err(taskFailed('disk full')));

      await exportAfterConfirming();

      expect(notify).toHaveBeenCalledWith(expect.objectContaining({
        message: 'actions.history_events_export.message.failure::disk full',
        severity: Severity.ERROR,
      }));
    });

    /** A cancellation is the user's own doing and the task centre already shows it. */
    it('should stay quiet when the task was cancelled', async () => {
      submitTask.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));

      await exportAfterConfirming();

      expect(notify).not.toHaveBeenCalled();
    });

    it('should report an error thrown on the way', async () => {
      submitTask.mockRejectedValue(new Error('boom'));

      await exportAfterConfirming();

      expect(notify).toHaveBeenCalledWith(expect.objectContaining({
        message: 'actions.history_events_export.message.failure::boom',
        severity: Severity.ERROR,
      }));
    });
  });
});
