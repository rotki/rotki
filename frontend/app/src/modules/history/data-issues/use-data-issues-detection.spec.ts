import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TaskFailed } from '@/modules/core/tasks/task-result';
import { useDataIssuesDetection } from '@/modules/history/data-issues/use-data-issues-detection';

const runTaskMock = vi.fn();
const triggerTaskMock = vi.fn(async (_task: string) => ({ taskId: 1 }));
const showErrorMessageMock = vi.fn<(title: string, message: string) => void>();
const reload = vi.fn<() => Promise<void>>();

vi.mock('@/modules/core/tasks/use-task-handler', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useTaskHandler: vi.fn(() => ({
      runTask: async (taskFn: () => Promise<unknown>, ...rest: unknown[]): Promise<unknown> => {
        await taskFn();
        return runTaskMock(taskFn, ...rest);
      },
    })),
  };
});

vi.mock('@/modules/core/tasks/use-task-api', () => ({
  useTaskApi: vi.fn(() => ({ triggerTask: triggerTaskMock })),
}));

vi.mock('@/modules/core/notifications/use-notifications', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useNotifications: vi.fn(() => ({ showErrorMessage: showErrorMessageMock })),
  };
});

describe('useDataIssuesDetection', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    reload.mockResolvedValue(undefined);
  });

  it('should trigger the current balance detection task and reload the issues', async () => {
    runTaskMock.mockResolvedValue(ok(true));
    const { detect, detecting } = useDataIssuesDetection(reload);

    await detect();

    expect(triggerTaskMock).toHaveBeenCalledWith('current_balance_detection');
    expect(reload).toHaveBeenCalledOnce();
    expect(detecting.value).toBe(false);
  });

  it('should show the backend message and skip the reload when the detection could not run', async () => {
    runTaskMock.mockResolvedValue(err(TaskFailed({ cause: new Error('still processing'), message: 'still processing' })));
    const { detect, detecting } = useDataIssuesDetection(reload);

    await detect();

    expect(showErrorMessageMock).toHaveBeenCalledOnce();
    expect(showErrorMessageMock.mock.calls[0][1]).toContain('still processing');
    expect(reload).not.toHaveBeenCalled();
    expect(detecting.value).toBe(false);
  });
});
