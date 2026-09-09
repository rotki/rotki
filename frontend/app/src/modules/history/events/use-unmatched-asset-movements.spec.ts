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

  /**
   * Re-imports the module under test so each case starts from empty state.
   *
   * @remarks
   * `useUnmatchedAssetMovements` is a `createSharedComposable` singleton, so its module-level refs
   * survive between tests unless the module registry is reset first.
   */
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

    /** A failed fetch leaves no movements behind, and must not leave the list loading forever. */
    it('should report a failed fetch and stop loading', async () => {
      spies.getUnmatchedAssetMovements.mockRejectedValueOnce(new Error('the backend said no'));
      const { useUnmatchedAssetMovements } = await importFresh();
      const { fetchUnmatchedAssetMovements, loading } = useUnmatchedAssetMovements();

      await fetchUnmatchedAssetMovements(false);

      expect(spies.showErrorMessage).toHaveBeenCalledWith(
        'actions.asset_movement_matching.fetch_error.title',
        expect.stringContaining('the backend said no'),
      );
      expect(get(loading)).toBe(false);
    });
  });

  /** The two lists are separate queries, and the ignored one is only worth re-reading sometimes. */
  describe('refreshUnmatchedAssetMovements', () => {
    it('should re-read both lists', async () => {
      spies.getUnmatchedAssetMovements.mockResolvedValue([]);
      const { useUnmatchedAssetMovements } = await importFresh();

      await useUnmatchedAssetMovements().refreshUnmatchedAssetMovements();

      expect(spies.getUnmatchedAssetMovements).toHaveBeenCalledTimes(2);
      expect(spies.getUnmatchedAssetMovements).toHaveBeenNthCalledWith(2, true);
    });

    it('should re-read only the unmatched list when asked to skip the ignored one', async () => {
      spies.getUnmatchedAssetMovements.mockResolvedValue([]);
      const { useUnmatchedAssetMovements } = await importFresh();

      await useUnmatchedAssetMovements().refreshUnmatchedAssetMovements(true);

      expect(spies.getUnmatchedAssetMovements).toHaveBeenCalledTimes(1);
    });
  });

  describe('matchAssetMovement', () => {
    it('should report a match and tell the rest of the app the events changed', async () => {
      spies.matchAssetMovements.mockResolvedValueOnce(true);
      const { useUnmatchedAssetMovements } = await importFresh();

      const result = await useUnmatchedAssetMovements().matchAssetMovement(1, [2, 3]);

      expect(spies.matchAssetMovements).toHaveBeenCalledWith(1, [2, 3]);
      expect(result).toEqual({ message: '', success: true });
      expect(spies.showSuccessMessage).toHaveBeenCalled();
      expect(spies.signalEventsModified).toHaveBeenCalledTimes(1);
    });

    /** A refused match changed nothing, so nothing is announced and nothing is invalidated. */
    it('should stay quiet when the match was refused', async () => {
      spies.matchAssetMovements.mockResolvedValueOnce(false);
      const { useUnmatchedAssetMovements } = await importFresh();

      const result = await useUnmatchedAssetMovements().matchAssetMovement(1, [2]);

      expect(result).toEqual({ message: '', success: false });
      expect(spies.showSuccessMessage).not.toHaveBeenCalled();
      expect(spies.signalEventsModified).not.toHaveBeenCalled();
    });

    it('should report a failure and hand the message back', async () => {
      spies.matchAssetMovements.mockRejectedValueOnce(new Error('the backend said no'));
      const { useUnmatchedAssetMovements } = await importFresh();

      const result = await useUnmatchedAssetMovements().matchAssetMovement(1, [2]);

      expect(result).toEqual({ message: 'the backend said no', success: false });
      expect(spies.showErrorMessage).toHaveBeenCalled();
      expect(spies.signalEventsModified).not.toHaveBeenCalled();
    });
  });

  /** Resolving as external is the same call with no matches, flagged as deliberate. */
  describe('resolveExternal', () => {
    it('should resolve the movement without naming any matches', async () => {
      spies.matchAssetMovements.mockResolvedValueOnce(true);
      const { useUnmatchedAssetMovements } = await importFresh();

      const result = await useUnmatchedAssetMovements().resolveExternal(1);

      expect(spies.matchAssetMovements).toHaveBeenCalledWith(1, undefined, true);
      expect(result).toEqual({ message: '', success: true });
      expect(spies.signalEventsModified).toHaveBeenCalledTimes(1);
    });

    /** The caller surfaces this one itself, with an undo, so a toast would be a second report. */
    it('should say nothing on success, since the caller reports it with an undo', async () => {
      spies.matchAssetMovements.mockResolvedValueOnce(true);
      const { useUnmatchedAssetMovements } = await importFresh();

      await useUnmatchedAssetMovements().resolveExternal(1);

      expect(spies.showSuccessMessage).not.toHaveBeenCalled();
    });

    it('should report a failure and hand the message back', async () => {
      spies.matchAssetMovements.mockRejectedValueOnce(new Error('the backend said no'));
      const { useUnmatchedAssetMovements } = await importFresh();

      const result = await useUnmatchedAssetMovements().resolveExternal(1);

      expect(result).toEqual({ message: 'the backend said no', success: false });
      expect(spies.showErrorMessage).toHaveBeenCalled();
      expect(spies.signalEventsModified).not.toHaveBeenCalled();
    });
  });
});
