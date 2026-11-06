import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import { Severity } from '@rotki/common';
import { err, ok, type Result } from 'plainfp/result';
import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { computed, type ComputedRef } from 'vue';
import { Cancelled, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useHistoryEventsExport } from '@/modules/history/events/use-history-events-export';

const { downloadHistoryEventsCSV, exportHistoryEventsCSV, interop, notify, submitTask } = vi.hoisted(() => ({
  downloadHistoryEventsCSV: vi.fn(async () => {}),
  exportHistoryEventsCSV: vi.fn(),
  interop: { appSession: false, openDirectory: vi.fn() },
  notify: vi.fn(),
  submitTask: vi.fn(),
}));

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

const filters: HistoryEventRequestPayload = {
  aggregateByGroupIds: true,
  limit: 10,
  location: 'ethereum',
  offset: 20,
};

function taskFailed(message: string): TaskError {
  return TaskFailed({ message });
}

async function runExport(matchExactEvents = false): Promise<void> {
  await useHistoryEventsExport(() => filters, () => matchExactEvents).exportCSV();
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
    interop.appSession = false;
    interop.openDirectory.mockResolvedValue('/tmp/export');
    exportHistoryEventsCSV.mockResolvedValue(true);
    submitTask.mockResolvedValue(ok(true));
  });

  it('should report the export as running while the task centre says so', () => {
    const { taskRunning } = useHistoryEventsExport(() => filters, () => false);

    expect(get(taskRunning)).toBe(true);
  });

  describe('choosing where the file goes', () => {
    it('should ask the app session for a directory', async () => {
      interop.appSession = true;

      await runExport();

      expect(interop.openDirectory).toHaveBeenCalledTimes(1);
      expect(submitTask).toHaveBeenCalledTimes(1);
    });

    it('should abandon the export when the directory picker is dismissed', async () => {
      interop.appSession = true;
      interop.openDirectory.mockResolvedValue(undefined);

      await runExport();

      expect(submitTask).not.toHaveBeenCalled();
      expect(notify).not.toHaveBeenCalled();
    });

    it('should not ask a browser session where to put it', async () => {
      await runExport();

      expect(interop.openDirectory).not.toHaveBeenCalled();
      expect(submitTask).toHaveBeenCalledTimes(1);
    });
  });

  /** The export covers everything the filters match, so the table's paging must not narrow it. */
  describe('what the backend is asked for', () => {
    it('should drop the paging and grouping the table was using', async () => {
      await runExport();
      await runSubmittedTask(ok(true));

      expect(exportHistoryEventsCSV).toHaveBeenCalledWith({
        location: 'ethereum',
        matchExactEvents: false,
      }, undefined);
    });

    it('should pass on whether the matched events were asked for', async () => {
      await runExport(true);
      await runSubmittedTask(ok(true));

      expect(exportHistoryEventsCSV).toHaveBeenCalledWith(
        expect.objectContaining({ matchExactEvents: true }),
        undefined,
      );
    });

    it('should send the directory the app session chose', async () => {
      interop.appSession = true;

      await runExport();
      await runSubmittedTask(ok(true));

      expect(exportHistoryEventsCSV).toHaveBeenCalledWith(expect.anything(), '/tmp/export');
    });
  });

  describe('reporting the outcome in an app session', () => {
    beforeEach(() => {
      interop.appSession = true;
    });

    it('should confirm the file was written', async () => {
      await runExport();

      expect(notify).toHaveBeenCalledWith(expect.objectContaining({
        message: 'actions.history_events_export.message.success',
        severity: Severity.INFO,
      }));
    });
  });

  describe('reporting the outcome in a browser session', () => {
    it('should stream the generated file back instead of announcing it', async () => {
      submitTask.mockResolvedValue(ok({ filePath: '/tmp/events.csv' }));

      await runExport();

      expect(downloadHistoryEventsCSV).toHaveBeenCalledWith('/tmp/events.csv');
      expect(notify).not.toHaveBeenCalled();
    });
  });

  describe('when the task fails', () => {
    it('should leave an actionable failure to its dock row', async () => {
      submitTask.mockResolvedValue(err(taskFailed('disk full')));

      await runExport();

      expect(notify).not.toHaveBeenCalled();
    });

    /** A cancellation is the user's own doing and the task centre already shows it. */
    it('should stay quiet when the task was cancelled', async () => {
      submitTask.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));

      await runExport();

      expect(notify).not.toHaveBeenCalled();
    });

    it('should report an error thrown on the way', async () => {
      submitTask.mockRejectedValue(new Error('boom'));

      await runExport();

      expect(notify).toHaveBeenCalledWith(expect.objectContaining({
        message: 'actions.history_events_export.message.failure::boom',
        severity: Severity.ERROR,
      }));
    });
  });
});
