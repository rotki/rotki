import type { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { createMock } from '@test/utils/create-mock';
import { err, ok } from 'plainfp/result';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { TaskFailed } from '@/modules/core/tasks/task-result';

const { spies } = vi.hoisted(() => ({
  spies: {
    getUnmatchedAssetMovements: vi.fn<(onlyIgnored?: boolean) => Promise<string[]>>(),
    fetchHistoryEvents: vi.fn(),
    matchAssetMovements: vi.fn(),
    triggerAssetMovementMatching: vi.fn(),
    getAssetMovementMatches: vi.fn(),
    unlinkAssetMovement: vi.fn(),
    showErrorMessage: vi.fn(),
    showSuccessMessage: vi.fn(),
    runTask: vi.fn(),
    submitTask: vi.fn(),
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

vi.mock('@/modules/task-center/use-native-task', async () => {
  const { runSpecWith } = await import('@test/utils/mocks/native-task');
  return {
    ...await vi.importActual<typeof import('@/modules/task-center/use-native-task')>('@/modules/task-center/use-native-task'),
    useNativeTask: (): object => ({
      statusOf: (): object => ({ active: false }),
      submitTask: spies.submitTask.mockImplementation(runSpecWith(spies.runTask)),
    }),
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

  describe('fetchUnmatchedAssetMovements', () => {
    it('should empty the unmatched count without loading events when the backend reports none', async () => {
      spies.getUnmatchedAssetMovements.mockResolvedValueOnce([]);
      const { useUnmatchedAssetMovements } = await importFresh();
      const { fetchUnmatchedAssetMovements, unmatchedCount } = useUnmatchedAssetMovements();

      await fetchUnmatchedAssetMovements(false);

      expect(get(unmatchedCount)).toBe(0);
      expect(spies.fetchHistoryEvents).not.toHaveBeenCalled();
    });

    it('should count the movements the backend still reports as unmatched', async () => {
      spies.getUnmatchedAssetMovements.mockResolvedValueOnce(['group-a']);
      spies.fetchHistoryEvents.mockResolvedValueOnce({
        entries: [{ entry: { asset: 'ETH', groupIdentifier: 'group-a' } }],
      });
      const { useUnmatchedAssetMovements } = await importFresh();
      const { fetchUnmatchedAssetMovements, unmatchedCount } = useUnmatchedAssetMovements();

      await fetchUnmatchedAssetMovements(false);

      expect(get(unmatchedCount)).toBe(1);
    });

    /** A background websocket message triggers this too, so a dialog would interrupt whatever the user is doing. */
    it('should keep a failed fetch for the list instead of a dialog, and stop loading', async () => {
      const failure = new Error('the backend said no');
      spies.getUnmatchedAssetMovements.mockRejectedValueOnce(failure);
      const { useUnmatchedAssetMovements } = await importFresh();
      const { fetchUnmatchedAssetMovements, ignoredError, loading, unmatchedError } = useUnmatchedAssetMovements();

      await fetchUnmatchedAssetMovements(false);

      expect(get(unmatchedError)).toBe(failure);
      expect(get(ignoredError)).toBeUndefined();
      expect(spies.showErrorMessage).not.toHaveBeenCalled();
      expect(get(loading)).toBe(false);
    });

    /** The action center counts these rows, so emptying them on a blip would hide its unmatched row. */
    it('should keep the rows of the last good fetch when a later one fails', async () => {
      spies.getUnmatchedAssetMovements.mockResolvedValueOnce(['group-a']).mockRejectedValueOnce(new Error('the backend said no'));
      spies.fetchHistoryEvents.mockResolvedValueOnce({
        entries: [{ entry: { asset: 'ETH', groupIdentifier: 'group-a' } }],
      });
      const { useUnmatchedAssetMovements } = await importFresh();
      const { fetchUnmatchedAssetMovements, unmatchedCount, unmatchedError } = useUnmatchedAssetMovements();
      await fetchUnmatchedAssetMovements(false);

      await fetchUnmatchedAssetMovements(false);

      expect(get(unmatchedCount)).toBe(1);
      expect(get(unmatchedError)).toBeInstanceOf(Error);
    });

    it('should clear the kept failure once a later fetch succeeds', async () => {
      spies.getUnmatchedAssetMovements.mockRejectedValueOnce(new Error('the backend said no')).mockResolvedValueOnce([]);
      const { useUnmatchedAssetMovements } = await importFresh();
      const { fetchUnmatchedAssetMovements, unmatchedError } = useUnmatchedAssetMovements();
      await fetchUnmatchedAssetMovements(false);

      await fetchUnmatchedAssetMovements(false);

      expect(get(unmatchedError)).toBeUndefined();
    });

    it('should stay quiet when the fetch is cancelled, as on a logout, and stop loading', async () => {
      const { useUnmatchedAssetMovements } = await importFresh();
      const { RequestCancelledError } = await import('@/modules/core/api/request-queue/errors');
      spies.getUnmatchedAssetMovements.mockRejectedValueOnce(new RequestCancelledError('No live session'));
      const { fetchUnmatchedAssetMovements, loading } = useUnmatchedAssetMovements();

      await fetchUnmatchedAssetMovements(false);

      expect(spies.showErrorMessage).not.toHaveBeenCalled();
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
      expect(result).toEqual({ success: true });
      expect(spies.showSuccessMessage).toHaveBeenCalled();
      expect(spies.signalEventsModified).toHaveBeenCalledTimes(1);
    });

    /** A refused match changed nothing, so nothing is announced or invalidated, but the panel still names it. */
    it('should hand a refused match back with a reason, announcing nothing', async () => {
      spies.matchAssetMovements.mockResolvedValueOnce(false);
      const { useUnmatchedAssetMovements } = await importFresh();

      const result = await useUnmatchedAssetMovements().matchAssetMovement(1, [2]);

      expect(result).toEqual({ message: new Error('common.change_not_applied'), success: false });
      expect(spies.showSuccessMessage).not.toHaveBeenCalled();
      expect(spies.signalEventsModified).not.toHaveBeenCalled();
    });

    it('should hand the thrown error back for the panel, instead of a dialog', async () => {
      spies.matchAssetMovements.mockRejectedValueOnce(new Error('the backend said no'));
      const { useUnmatchedAssetMovements } = await importFresh();

      const result = await useUnmatchedAssetMovements().matchAssetMovement(1, [2]);

      expect(result).toMatchObject({ message: { message: 'the backend said no' }, success: false });
      expect(spies.showErrorMessage).not.toHaveBeenCalled();
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
      expect(result).toEqual({ success: true });
      expect(spies.signalEventsModified).toHaveBeenCalledTimes(1);
    });

    /** The caller surfaces this one itself, with an undo, so a toast would be a second report. */
    it('should say nothing on success, since the caller reports it with an undo', async () => {
      spies.matchAssetMovements.mockResolvedValueOnce(true);
      const { useUnmatchedAssetMovements } = await importFresh();

      await useUnmatchedAssetMovements().resolveExternal(1);

      expect(spies.showSuccessMessage).not.toHaveBeenCalled();
    });

    it('should hand the thrown error back for the panel, instead of a dialog', async () => {
      spies.matchAssetMovements.mockRejectedValueOnce(new Error('the backend said no'));
      const { useUnmatchedAssetMovements } = await importFresh();

      const result = await useUnmatchedAssetMovements().resolveExternal(1);

      expect(result).toMatchObject({ message: { message: 'the backend said no' }, success: false });
      expect(spies.showErrorMessage).not.toHaveBeenCalled();
      expect(spies.signalEventsModified).not.toHaveBeenCalled();
    });
  });

  describe('triggerAssetMovementAutoMatching', () => {
    it('should re-read the unmatched list and signal modified events once matching finishes', async () => {
      spies.runTask.mockResolvedValueOnce(ok(true));
      spies.getUnmatchedAssetMovements.mockResolvedValue([]);
      const { useUnmatchedAssetMovements } = await importFresh();

      await useUnmatchedAssetMovements().triggerAssetMovementAutoMatching();

      expect(spies.signalEventsModified).toHaveBeenCalledOnce();
    });

    it('should leave a failure to its task centre row, with no message of its own', async () => {
      spies.runTask.mockResolvedValueOnce(err(TaskFailed({ message: 'the backend said no' })));
      const { useUnmatchedAssetMovements } = await importFresh();

      await useUnmatchedAssetMovements().triggerAssetMovementAutoMatching();

      expect(spies.submitTask).toHaveBeenCalledOnce();
      expect(spies.showErrorMessage).not.toHaveBeenCalled();
      expect(spies.signalEventsModified).not.toHaveBeenCalled();
    });
  });
});
