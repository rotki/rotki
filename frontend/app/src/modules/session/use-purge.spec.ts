import { runSpecWith } from '@test/utils/mocks/native-task';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import { Purgeable } from './purge';
import { useSessionPurge } from './use-purge';

const refreshGeneralCacheTask = vi.fn();
const runTaskResult = vi.fn();

const submitTask = vi.fn(runSpecWith(runTaskResult));

vi.mock('@/modules/session/api/use-session-api', () => ({
  useSessionApi: (): object => ({ refreshGeneralCacheTask }),
}));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: (): object => ({ cancelByType: (): (() => void) => vi.fn(), runTaskResult, statusOf: vi.fn(), submitTask }),
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

      await expect(useSessionPurge().purgeData(Purgeable.TRANSACTIONS, '', deleteData)).rejects.toThrow();

      const outcome = await submitTask.mock.results[0].value;
      expect(outcome).toStrictEqual(err(TaskFailed({ cause: new Error('nope'), message: 'nope' })));
    });

    it('should reject when the deletion fails, so the purge page does not report success', async () => {
      const deleteData = vi.fn().mockRejectedValue(new Error('nope'));

      await expect(useSessionPurge().purgeData(Purgeable.TRANSACTIONS, 'eth', deleteData)).rejects.toThrow('nope');
    });

    it('should resolve when the deletion succeeds', async () => {
      await expect(useSessionPurge().purgeData(Purgeable.TRANSACTIONS, 'eth', vi.fn().mockResolvedValue(undefined))).resolves.toBeUndefined();
    });
  });

  describe('refreshGeneralCache', () => {
    it('should run the refresh task', async () => {
      await useSessionPurge().refreshGeneralCache('opensea');
      expect(submitTask).toHaveBeenCalledOnce();
    });

    it('should reject when the user cancelled the refresh', async () => {
      runTaskResult.mockResolvedValue(err(Cancelled({ message: 'Request cancelled' })));
      await expect(useSessionPurge().refreshGeneralCache('opensea')).rejects.toThrow('Request cancelled');
      expect(submitTask).toHaveBeenCalledOnce();
    });

    it('should reject on a failure, so the refresh page does not report success', async () => {
      runTaskResult.mockResolvedValue(err(TaskFailed({ message: 'boom' })));
      await expect(useSessionPurge().refreshGeneralCache('opensea')).rejects.toThrow('boom');
    });

    it('should resolve when the refresh succeeds', async () => {
      await expect(useSessionPurge().refreshGeneralCache('opensea')).resolves.toBeUndefined();
    });
  });
});
