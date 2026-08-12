import type { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { type NotificationData, NotificationGroup } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { spies } = vi.hoisted(() => ({
  spies: {
    getUnmatchedAssetMovements: vi.fn<(onlyIgnored?: boolean) => Promise<string[]>>(),
    fetchHistoryEvents: vi.fn(),
    matchAssetMovements: vi.fn(),
    triggerAssetMovementMatching: vi.fn(),
    getAssetMovementMatches: vi.fn(),
    unlinkAssetMovement: vi.fn(),
    removeMatching: vi.fn<(predicate: (n: NotificationData) => boolean) => void>(),
    showErrorMessage: vi.fn(),
    showSuccessMessage: vi.fn(),
    runTask: vi.fn(),
    useIsTaskRunning: vi.fn(() => ref(false)),
    signalEventsModified: vi.fn(),
    getAssetInfo: vi.fn(() => ({ assetType: 'crypto' })),
  },
}));

vi.mock('@/modules/history/api/events/use-asset-movement-matching-api', () => ({
  useAssetMovementMatchingApi: (): object => ({
    getAssetMovementMatches: spies.getAssetMovementMatches,
    getUnmatchedAssetMovements: spies.getUnmatchedAssetMovements,
    matchAssetMovements: spies.matchAssetMovements,
    triggerAssetMovementMatching: spies.triggerAssetMovementMatching,
    unlinkAssetMovement: spies.unlinkAssetMovement,
  }),
}));

vi.mock('@/modules/history/api/events/use-history-events-api', () => ({
  useHistoryEventsApi: (): ReturnType<typeof useHistoryEventsApi> => createMock<ReturnType<typeof useHistoryEventsApi>>({
    fetchHistoryEvents: spies.fetchHistoryEvents,
  }),
}));

// Mocked outright rather than spread over `...actual`: importActual evaluates the real
// notifications graph, which costs ~1.2s to import.
// `getErrorMessage` is a pure helper re-exported from a light module, so take it from there.
vi.mock('@/modules/core/notifications/use-notifications', async () => ({
  getErrorMessage: (await vi.importActual<typeof import('@/modules/core/common/logging/error-handling')>(
    '@/modules/core/common/logging/error-handling',
  )).getErrorMessage,
  useNotifications: (): object => ({
    removeMatching: spies.removeMatching,
    showErrorMessage: spies.showErrorMessage,
    showSuccessMessage: spies.showSuccessMessage,
  }),
}));

vi.mock('@/modules/core/tasks/use-task-handler', async () => {
  const actual = await vi.importActual<typeof import('@/modules/core/tasks/use-task-handler')>(
    '@/modules/core/tasks/use-task-handler',
  );
  return {
    ...actual,
    useTaskHandler: (): object => ({ runTask: spies.runTask }),
  };
});

vi.mock('@/modules/core/tasks/use-task-store', () => ({
  useTaskStore: (): object => ({ useIsTaskRunning: spies.useIsTaskRunning }),
}));

vi.mock('@/modules/history/use-history-store', () => ({
  useHistoryStore: (): object => ({ signalEventsModified: spies.signalEventsModified }),
}));

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): object => ({ getAssetInfo: spies.getAssetInfo }),
}));

vi.mock('@/modules/premium/use-feature-access', async () => {
  const actual = await vi.importActual<typeof import('@/modules/premium/use-feature-access')>(
    '@/modules/premium/use-feature-access',
  );
  return {
    ...actual,
    useFeatureAccess: (): object => ({
      allowed: ref(true),
      minimumTier: ref(null),
    }),
  };
});

describe('use-unmatched-asset-movements', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // `useUnmatchedAssetMovements` is a `createSharedComposable` singleton whose
  // module-level refs would otherwise persist between tests; re-import per test
  // so each starts from fresh state.
  async function importFresh(): Promise<typeof import('@/modules/history/events/use-unmatched-asset-movements')> {
    vi.resetModules();
    return import('@/modules/history/events/use-unmatched-asset-movements');
  }

  describe('fetchUnmatchedAssetMovements clears stale notification', () => {
    it('should clear the unmatched-movements notification when the unmatched list becomes empty', async () => {
      spies.getUnmatchedAssetMovements.mockResolvedValueOnce([]);
      const { useUnmatchedAssetMovements } = await importFresh();
      const { fetchUnmatchedAssetMovements } = useUnmatchedAssetMovements();

      await fetchUnmatchedAssetMovements(false);

      expect(spies.removeMatching).toHaveBeenCalledTimes(1);
      const predicate = spies.removeMatching.mock.calls[0][0];
      expect(predicate(createMock<NotificationData>({ group: NotificationGroup.UNMATCHED_ASSET_MOVEMENTS }))).toBe(true);
      expect(predicate(createMock<NotificationData>())).toBe(false);
    });

    it('should not clear the notification when fetching the ignored list', async () => {
      spies.getUnmatchedAssetMovements.mockResolvedValueOnce([]);
      const { useUnmatchedAssetMovements } = await importFresh();
      const { fetchUnmatchedAssetMovements } = useUnmatchedAssetMovements();

      await fetchUnmatchedAssetMovements(true);

      expect(spies.removeMatching).not.toHaveBeenCalled();
    });

    it('should not clear the notification when there are still unmatched movements', async () => {
      spies.getUnmatchedAssetMovements.mockResolvedValueOnce(['group-a']);
      spies.fetchHistoryEvents.mockResolvedValueOnce({
        entries: [{ entry: { asset: 'ETH', groupIdentifier: 'group-a' } }],
      });
      const { useUnmatchedAssetMovements } = await importFresh();
      const { fetchUnmatchedAssetMovements } = useUnmatchedAssetMovements();

      await fetchUnmatchedAssetMovements(false);

      expect(spies.removeMatching).not.toHaveBeenCalled();
    });
  });
});
