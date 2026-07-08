import type { TaskResult } from '@/modules/core/tasks/use-task-handler';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Section } from '@/modules/core/common/status';
import { Purgeable } from './purge';
import { useSessionPurge } from './use-purge';

const refreshGeneralCacheTask = vi.fn();
const resetStatus = vi.fn();
const runTask = vi.fn();
const notifyError = vi.fn();
const markAllProtocolCacheCancelled = vi.fn();
const resetProtocolCacheUpdatesStatus = vi.fn();

vi.mock('@/modules/session/api/use-session-api', () => ({
  useSessionApi: (): object => ({ refreshGeneralCacheTask }),
}));

vi.mock('@/modules/core/common/use-status-store', () => ({
  useStatusStore: (): object => ({ resetStatus }),
}));

vi.mock('@/modules/core/tasks/use-task-handler', () => ({
  useTaskHandler: (): object => ({ runTask }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: (): object => ({ notifyError }),
}));

vi.mock('@/modules/history/use-protocol-cache-status-store', () => ({
  useProtocolCacheStatusStore: (): object => ({ markAllProtocolCacheCancelled, resetProtocolCacheUpdatesStatus }),
}));

const success: TaskResult<boolean> = { success: true, result: true };

describe('useSessionPurge', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    runTask.mockResolvedValue(success);
  });

  describe('purgeCache', () => {
    it.each([Purgeable.CENTRALIZED_EXCHANGES, Purgeable.TRANSACTIONS])(
      'should reset the history status for %s',
      (purgeable) => {
        useSessionPurge().purgeCache(purgeable, '');
        expect(resetStatus).toHaveBeenCalledWith(Section.HISTORY);
      },
    );

    it('should not reset any status for unrelated purgeables', () => {
      useSessionPurge().purgeCache(Purgeable.DEFI_MODULES, '');
      expect(resetStatus).not.toHaveBeenCalled();
    });
  });

  describe('refreshGeneralCache', () => {
    it('should reset the protocol cache and run the refresh task', async () => {
      await useSessionPurge().refreshGeneralCache('opensea');
      expect(resetProtocolCacheUpdatesStatus).toHaveBeenCalledOnce();
      expect(runTask).toHaveBeenCalledOnce();
      expect(notifyError).not.toHaveBeenCalled();
    });

    it('should mark the protocol cache cancelled when the task is cancelled', async () => {
      runTask.mockResolvedValue({ success: false, message: '', cancelled: true, backendCancelled: false, skipped: false });
      await useSessionPurge().refreshGeneralCache('opensea');
      expect(markAllProtocolCacheCancelled).toHaveBeenCalledOnce();
      expect(notifyError).not.toHaveBeenCalled();
    });

    it('should notify on an actionable failure', async () => {
      runTask.mockResolvedValue({ success: false, message: 'boom', cancelled: false, backendCancelled: false, skipped: false });
      await useSessionPurge().refreshGeneralCache('opensea');
      expect(notifyError).toHaveBeenCalledOnce();
      expect(markAllProtocolCacheCancelled).not.toHaveBeenCalled();
    });

    it('should stay silent when the task is skipped', async () => {
      runTask.mockResolvedValue({ success: false, message: '', cancelled: false, backendCancelled: false, skipped: true });
      await useSessionPurge().refreshGeneralCache('opensea');
      expect(notifyError).not.toHaveBeenCalled();
      expect(markAllProtocolCacheCancelled).not.toHaveBeenCalled();
    });
  });
});
