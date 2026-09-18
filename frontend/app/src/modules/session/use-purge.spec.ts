import { runSpecWith } from '@test/utils/mocks/native-task';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import { Purgeable } from './purge';
import { useSessionPurge } from './use-purge';

const refreshGeneralCacheTask = vi.fn();
const runTaskResult = vi.fn();
const notifyError = vi.fn();

const submitTask = vi.fn(runSpecWith(runTaskResult));

vi.mock('@/modules/session/api/use-session-api', () => ({
  useSessionApi: (): object => ({ refreshGeneralCacheTask }),
}));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: (): object => ({ cancelByType: (): (() => void) => vi.fn(), runTaskResult, statusOf: vi.fn(), submitTask }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: (): object => ({ notifyError }),
}));

describe('useSessionPurge', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    runTaskResult.mockResolvedValue(ok(true));
  });

  describe('purgeData', () => {
    it('should run the deletion as an activity named after the source', async () => {
      const deleteData = vi.fn().mockResolvedValue(undefined);

      await useSessionPurge().purgeData(Purgeable.TRANSACTIONS, 'eth', deleteData);

      expect(deleteData).toHaveBeenCalledTimes(1);
      expect(submitTask).toHaveBeenCalledWith(expect.objectContaining({ id: 'purge:transactions:eth' }));
    });

    it('should name the activity by source alone when there is no value', async () => {
      await useSessionPurge().purgeData(Purgeable.CENTRALIZED_EXCHANGES, '', vi.fn().mockResolvedValue(undefined));

      expect(submitTask).toHaveBeenCalledWith(expect.objectContaining({ id: 'purge:centralized_exchanges' }));
    });

    it('should surface a failed deletion as a failed activity', async () => {
      const deleteData = vi.fn().mockRejectedValue(new Error('nope'));

      await useSessionPurge().purgeData(Purgeable.TRANSACTIONS, '', deleteData);

      const outcome = await submitTask.mock.results[0].value;
      expect(outcome).toStrictEqual(err(TaskFailed({ cause: new Error('nope'), message: 'nope' })));
    });
  });

  describe('refreshGeneralCache', () => {
    it('should run the refresh task', async () => {
      await useSessionPurge().refreshGeneralCache('opensea');
      expect(submitTask).toHaveBeenCalledOnce();
      expect(notifyError).not.toHaveBeenCalled();
    });

    it('should not notify when the user cancelled the refresh', async () => {
      runTaskResult.mockResolvedValue(err(Cancelled({ message: '' })));
      await useSessionPurge().refreshGeneralCache('opensea');
      expect(submitTask).toHaveBeenCalledOnce();
      expect(notifyError).not.toHaveBeenCalled();
    });

    it('should notify on an actionable failure', async () => {
      runTaskResult.mockResolvedValue(err(TaskFailed({ message: 'boom' })));
      await useSessionPurge().refreshGeneralCache('opensea');
      expect(notifyError).toHaveBeenCalledOnce();
    });
  });
});
