import type { TaskFailure } from '@/modules/core/tasks/use-task-handler';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiKeyMissingError } from '@/modules/core/api/types/errors';
import { OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';
import { SyncWarningSource, useSyncWarningsStore } from '@/modules/shell/sync-progress/use-sync-warnings-store';
import { useRefreshHandlers } from './use-refresh-handlers';

const mockNotifyError = vi.fn();
const mockRunTask = vi.fn();

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({ notifyError: mockNotifyError })),
}));

vi.mock('@/modules/core/tasks/use-task-handler', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/modules/core/tasks/use-task-handler')>();
  return {
    ...actual,
    useTaskHandler: vi.fn(() => ({
      runTask: mockRunTask,
      cancelTask: vi.fn(),
      cancelTaskByTaskType: vi.fn(),
      handleResult: vi.fn(),
    })),
  };
});

vi.mock('@/modules/history/api/events/use-history-events-api', () => ({
  useHistoryEventsApi: vi.fn(() => ({
    queryExchangeEvents: vi.fn(),
    queryOnlineHistoryEvents: vi.fn(),
  })),
}));

vi.mock('@/modules/history/use-events-query-status-store', () => ({
  useEventsQueryStatusStore: vi.fn(() => ({ markLocationCancelled: vi.fn() })),
}));

vi.mock('@/modules/session/use-module-enabled', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/modules/session/use-module-enabled')>();
  return {
    ...actual,
    useModuleEnabled: vi.fn(() => ({ enabled: ref(true) })),
  };
});

vi.mock('@/modules/integrations/monerium/use-monerium-auth', () => ({
  useMoneriumOAuth: vi.fn(() => ({
    authenticated: ref(true),
    refreshStatus: vi.fn().mockResolvedValue(undefined),
  })),
}));

vi.mock('@/modules/premium/use-feature-access', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/modules/premium/use-feature-access')>();
  return {
    ...actual,
    useFeatureAccess: vi.fn(() => ({ allowed: ref(true) })),
  };
});

vi.mock('@/modules/settings/api-keys/external/use-external-api-keys', () => ({
  useExternalApiKeys: vi.fn(() => ({ getApiKey: vi.fn(() => 'fake-key') })),
}));

function makeFailure(overrides: Partial<TaskFailure>): TaskFailure {
  return {
    backendCancelled: false,
    cancelled: false,
    message: 'failure',
    skipped: false,
    success: false,
    ...overrides,
  };
}

describe('useRefreshHandlers', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  describe('queryOnlineEvent', () => {
    it('should add a warning instead of notifying on ApiKeyMissingError', async () => {
      const error = new ApiKeyMissingError('Querying beaconcha.in failed due to missing API key');
      mockRunTask.mockResolvedValueOnce(makeFailure({ error, message: error.message }));

      const { queryOnlineEvent } = useRefreshHandlers();
      await queryOnlineEvent(OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS);

      const warnings = useSyncWarningsStore();
      expect(get(warnings.warnings)).toHaveLength(1);
      expect(get(warnings.warnings)[0]).toMatchObject({
        key: OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS,
        source: SyncWarningSource.ONLINE_EVENTS,
      });
      expect(get(warnings.warnings)[0].message).toContain('warning.missing_api_key.beaconchain');
      expect(get(warnings.warnings)[0].message).toContain('query_type.block_productions');
      expect(mockNotifyError).not.toHaveBeenCalled();
    });

    it('should notifyError on a generic failure (no warning added)', async () => {
      mockRunTask.mockResolvedValueOnce(makeFailure({ error: new Error('boom'), message: 'boom' }));

      const { queryOnlineEvent } = useRefreshHandlers();
      await queryOnlineEvent(OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS);

      const warnings = useSyncWarningsStore();
      expect(get(warnings.warnings)).toEqual([]);
      expect(mockNotifyError).toHaveBeenCalledOnce();
    });

    it('should ignore cancelled outcomes', async () => {
      mockRunTask.mockResolvedValueOnce(makeFailure({ cancelled: true, message: 'cancelled' }));

      const { queryOnlineEvent } = useRefreshHandlers();
      await queryOnlineEvent(OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS);

      const warnings = useSyncWarningsStore();
      expect(get(warnings.warnings)).toEqual([]);
      expect(mockNotifyError).not.toHaveBeenCalled();
    });
  });

  describe('resetOnlineWarnings', () => {
    it('should clear the warnings store', () => {
      const warningsStore = useSyncWarningsStore();
      warningsStore.addWarning({
        key: OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS,
        message: 'x',
        source: SyncWarningSource.ONLINE_EVENTS,
      });
      expect(get(warningsStore.warnings)).toHaveLength(1);

      const { resetOnlineWarnings } = useRefreshHandlers();
      resetOnlineWarnings();

      expect(get(warningsStore.warnings)).toEqual([]);
    });
  });
});
