import { NotificationGroup } from '@rotki/common';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { spies } = vi.hoisted(() => ({
  spies: {
    getUnmatchedBridgeTransactions: vi.fn<(onlyIgnored?: boolean) => Promise<string[]>>(),
    fetchHistoryEvents: vi.fn(),
    matchBridgeTransactions: vi.fn(),
    triggerBridgeMatching: vi.fn(),
    getBridgeMatches: vi.fn(),
    unlinkBridgeTransaction: vi.fn(),
    removeMatching: vi.fn<(predicate: (n: { group?: string }) => boolean) => void>(),
    showErrorMessage: vi.fn(),
    showSuccessMessage: vi.fn(),
    runTask: vi.fn(),
    useIsTaskRunning: vi.fn(() => ref(false)),
    signalEventsModified: vi.fn(),
  },
}));

vi.mock('@/modules/history/api/events/use-bridge-matching-api', () => ({
  useBridgeMatchingApi: (): object => ({
    getBridgeMatches: spies.getBridgeMatches,
    getUnmatchedBridgeTransactions: spies.getUnmatchedBridgeTransactions,
    matchBridgeTransactions: spies.matchBridgeTransactions,
    triggerBridgeMatching: spies.triggerBridgeMatching,
    unlinkBridgeTransaction: spies.unlinkBridgeTransaction,
  }),
}));

vi.mock('@/modules/history/api/events/use-history-events-api', () => ({
  useHistoryEventsApi: (): object => ({
    fetchHistoryEvents: spies.fetchHistoryEvents,
  }),
}));

vi.mock('@/modules/core/notifications/use-notifications', async () => {
  const actual = await vi.importActual<typeof import('@/modules/core/notifications/use-notifications')>(
    '@/modules/core/notifications/use-notifications',
  );
  return {
    ...actual,
    useNotifications: (): object => ({
      removeMatching: spies.removeMatching,
      showErrorMessage: spies.showErrorMessage,
      showSuccessMessage: spies.showSuccessMessage,
    }),
  };
});

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

describe('use-unmatched-bridge-transactions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // `useUnmatchedBridgeTransactions` is a `createSharedComposable` singleton whose
  // module-level refs would otherwise persist between tests; re-import per test
  // so each starts from fresh state.
  async function importFresh(): Promise<typeof import('@/modules/history/events/use-unmatched-bridge-transactions')> {
    vi.resetModules();
    return import('@/modules/history/events/use-unmatched-bridge-transactions');
  }

  describe('fetchUnmatchedBridgeTransactions', () => {
    it('should clear the unmatched-bridges notification when the unmatched list becomes empty', async () => {
      spies.getUnmatchedBridgeTransactions.mockResolvedValueOnce([]);
      const { useUnmatchedBridgeTransactions } = await importFresh();
      const { fetchUnmatchedBridgeTransactions } = useUnmatchedBridgeTransactions();

      await fetchUnmatchedBridgeTransactions(false);

      expect(spies.removeMatching).toHaveBeenCalledTimes(1);
      const [predicate] = spies.removeMatching.mock.calls[0];
      expect(predicate({ group: NotificationGroup.UNMATCHED_BRIDGE_TRANSACTIONS })).toBe(true);
      expect(predicate({ group: 'OTHER' })).toBe(false);
    });

    it('should not clear the notification when fetching the ignored list', async () => {
      spies.getUnmatchedBridgeTransactions.mockResolvedValueOnce([]);
      const { useUnmatchedBridgeTransactions } = await importFresh();
      const { fetchUnmatchedBridgeTransactions } = useUnmatchedBridgeTransactions();

      await fetchUnmatchedBridgeTransactions(true);

      expect(spies.removeMatching).not.toHaveBeenCalled();
    });

    it('should expand group identifiers to events with direction and bridge extra data', async () => {
      spies.getUnmatchedBridgeTransactions.mockResolvedValueOnce(['group-a']);
      spies.fetchHistoryEvents.mockResolvedValueOnce({
        entries: [{
          entry: {
            asset: 'ETH',
            eventSubtype: 'bridge',
            eventType: 'deposit',
            extraData: { bridge: { toAddress: '0xdef', toChain: 'optimism' } },
            groupIdentifier: 'group-a',
            identifier: 7,
          },
        }],
      });
      const { useUnmatchedBridgeTransactions } = await importFresh();
      const { fetchUnmatchedBridgeTransactions, unmatchedTransactions } = useUnmatchedBridgeTransactions();

      await fetchUnmatchedBridgeTransactions(false);

      expect(spies.removeMatching).not.toHaveBeenCalled();
      expect(get(unmatchedTransactions)).toHaveLength(1);
      expect(get(unmatchedTransactions)[0]).toMatchObject({
        asset: 'ETH',
        bridge: { toAddress: '0xdef', toChain: 'optimism' },
        direction: 'deposit',
        groupIdentifier: 'group-a',
        identifier: 7,
      });
    });

    // The backend returns each event of a group as its own top-level row (verified against a
    // real unmatched bridge group), so the gas fee event arrives as a separate row before the
    // bridge leg rather than alongside it in one array.
    it('should pick the bridge leg and not the gas fee event of the transaction group', async () => {
      spies.getUnmatchedBridgeTransactions.mockResolvedValueOnce(['group-a']);
      spies.fetchHistoryEvents.mockResolvedValueOnce({
        entries: [{
          entry: {
            asset: 'ETH',
            eventSubtype: 'fee',
            eventType: 'spend',
            groupIdentifier: 'group-a',
            identifier: 1,
            sequenceIndex: 0,
          },
        }, {
          entry: {
            asset: 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
            eventSubtype: 'bridge',
            eventType: 'deposit',
            extraData: { bridge: { toAddress: '0xdef', toChain: 'optimism' } },
            groupIdentifier: 'group-a',
            identifier: 2,
            sequenceIndex: 233,
          },
        }],
      });
      const { useUnmatchedBridgeTransactions } = await importFresh();
      const { fetchUnmatchedBridgeTransactions, unmatchedTransactions } = useUnmatchedBridgeTransactions();

      await fetchUnmatchedBridgeTransactions(false);

      expect(get(unmatchedTransactions)[0]).toMatchObject({
        asset: 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
        bridge: { toAddress: '0xdef', toChain: 'optimism' },
        direction: 'deposit',
        identifier: 2,
      });
    });

    it('should keep the withdrawal direction for an orphan withdrawal leg', async () => {
      spies.getUnmatchedBridgeTransactions.mockResolvedValueOnce(['group-b']);
      spies.fetchHistoryEvents.mockResolvedValueOnce({
        entries: [{
          entry: {
            asset: 'ETH',
            eventSubtype: 'fee',
            eventType: 'spend',
            groupIdentifier: 'group-b',
            identifier: 3,
          },
        }, {
          entry: {
            asset: 'ETH',
            eventSubtype: 'bridge',
            eventType: 'withdrawal',
            groupIdentifier: 'group-b',
            identifier: 4,
          },
        }],
      });
      const { useUnmatchedBridgeTransactions } = await importFresh();
      const { fetchUnmatchedBridgeTransactions, unmatchedTransactions } = useUnmatchedBridgeTransactions();

      await fetchUnmatchedBridgeTransactions(false);

      expect(get(unmatchedTransactions)[0]).toMatchObject({
        direction: 'withdrawal',
        identifier: 4,
      });
    });

    // A leg resolved as external is turned into a bridge spend/receive, so its direction can
    // no longer come from the event type and has to come from the recorded matchedBridge stamp.
    it('should derive the direction of an external-resolved leg from the matched bridge stamp', async () => {
      spies.getUnmatchedBridgeTransactions.mockResolvedValueOnce(['group-d']);
      spies.fetchHistoryEvents.mockResolvedValueOnce({
        entries: [{
          entry: {
            asset: 'ETH',
            eventSubtype: 'bridge',
            eventType: 'receive',
            extraData: { matchedBridge: { direction: 'withdrawal', resolution: 'external' } },
            groupIdentifier: 'group-d',
            identifier: 6,
          },
        }],
      });
      const { useUnmatchedBridgeTransactions } = await importFresh();
      const { fetchUnmatchedBridgeTransactions, ignoredTransactions } = useUnmatchedBridgeTransactions();

      await fetchUnmatchedBridgeTransactions(true);

      expect(get(ignoredTransactions)).toHaveLength(1);
      expect(get(ignoredTransactions)[0]).toMatchObject({
        direction: 'withdrawal',
        groupIdentifier: 'group-d',
      });
    });

    // A transaction can carry more than one bridge leg. Acting on a leg that was already
    // resolved as external would send the backend an event that is no longer a bridge
    // deposit/withdrawal, so the raw leg must win regardless of row order.
    it('should prefer the raw bridge leg over a leg already resolved as external', async () => {
      spies.getUnmatchedBridgeTransactions.mockResolvedValueOnce(['group-e']);
      spies.fetchHistoryEvents.mockResolvedValueOnce({
        entries: [{
          entry: {
            asset: 'ETH',
            eventSubtype: 'bridge',
            eventType: 'spend',
            extraData: { matchedBridge: { direction: 'deposit', resolution: 'external' } },
            groupIdentifier: 'group-e',
            identifier: 7,
          },
        }, {
          entry: {
            asset: 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
            eventSubtype: 'bridge',
            eventType: 'deposit',
            groupIdentifier: 'group-e',
            identifier: 8,
          },
        }],
      });
      const { useUnmatchedBridgeTransactions } = await importFresh();
      const { fetchUnmatchedBridgeTransactions, unmatchedTransactions } = useUnmatchedBridgeTransactions();

      await fetchUnmatchedBridgeTransactions(false);

      expect(get(unmatchedTransactions)).toHaveLength(1);
      expect(get(unmatchedTransactions)[0]).toMatchObject({
        direction: 'deposit',
        identifier: 8,
      });
    });

    it('should skip a group that contains no bridge event', async () => {
      spies.getUnmatchedBridgeTransactions.mockResolvedValueOnce(['group-c']);
      spies.fetchHistoryEvents.mockResolvedValueOnce({
        entries: [{
          entry: {
            asset: 'ETH',
            eventSubtype: 'fee',
            eventType: 'spend',
            groupIdentifier: 'group-c',
            identifier: 5,
          },
        }],
      });
      const { useUnmatchedBridgeTransactions } = await importFresh();
      const { fetchUnmatchedBridgeTransactions, unmatchedTransactions } = useUnmatchedBridgeTransactions();

      await fetchUnmatchedBridgeTransactions(false);

      expect(get(unmatchedTransactions)).toHaveLength(0);
    });
  });

  describe('matchBridgeTransaction', () => {
    it('should signal modified events and notify on success', async () => {
      spies.matchBridgeTransactions.mockResolvedValueOnce(true);
      const { useUnmatchedBridgeTransactions } = await importFresh();
      const { matchBridgeTransaction } = useUnmatchedBridgeTransactions();

      const result = await matchBridgeTransaction(1, [2, 3]);

      expect(result.success).toBe(true);
      expect(spies.matchBridgeTransactions).toHaveBeenCalledWith(1, [2, 3]);
      expect(spies.showSuccessMessage).toHaveBeenCalledOnce();
      expect(spies.signalEventsModified).toHaveBeenCalledOnce();
    });

    it('should report failure and show an error message when the call throws', async () => {
      spies.matchBridgeTransactions.mockRejectedValueOnce(new Error('boom'));
      const { useUnmatchedBridgeTransactions } = await importFresh();
      const { matchBridgeTransaction } = useUnmatchedBridgeTransactions();

      const result = await matchBridgeTransaction(1, [2]);

      expect(result.success).toBe(false);
      expect(spies.showErrorMessage).toHaveBeenCalledOnce();
      expect(spies.signalEventsModified).not.toHaveBeenCalled();
    });
  });

  describe('resolveExternal', () => {
    it('should resolve a deposit as external and signal modified events', async () => {
      spies.matchBridgeTransactions.mockResolvedValueOnce(true);
      const { useUnmatchedBridgeTransactions } = await importFresh();
      const { resolveExternal } = useUnmatchedBridgeTransactions();

      const result = await resolveExternal(9);

      expect(result.success).toBe(true);
      expect(spies.matchBridgeTransactions).toHaveBeenCalledWith(9, undefined, true);
      expect(spies.showSuccessMessage).toHaveBeenCalledOnce();
      expect(spies.signalEventsModified).toHaveBeenCalledOnce();
    });

    it('should report failure when resolving as external throws', async () => {
      spies.matchBridgeTransactions.mockRejectedValueOnce(new Error('boom'));
      const { useUnmatchedBridgeTransactions } = await importFresh();
      const { resolveExternal } = useUnmatchedBridgeTransactions();

      const result = await resolveExternal(9);

      expect(result.success).toBe(false);
      expect(spies.showErrorMessage).toHaveBeenCalledOnce();
    });
  });

  describe('autoMatchBridgeTransaction', () => {
    it('should link the close matches when suggestions are found', async () => {
      spies.getBridgeMatches.mockResolvedValueOnce({ closeMatches: [11, 12], otherEvents: [] });
      spies.matchBridgeTransactions.mockResolvedValueOnce(true);
      const { useUnmatchedBridgeTransactions } = await importFresh();
      const { autoMatchBridgeTransaction } = useUnmatchedBridgeTransactions();

      const matched = await autoMatchBridgeTransaction({
        groupIdentifier: 'group-a',
        identifier: 5,
        timeRange: 3600,
        tolerance: '0.01',
      });

      expect(matched).toBe(true);
      expect(spies.getBridgeMatches).toHaveBeenCalledWith('group-a', 3600, false, '0.01');
      expect(spies.matchBridgeTransactions).toHaveBeenCalledWith(5, [11, 12]);
    });

    it('should not link anything when there are no close matches', async () => {
      spies.getBridgeMatches.mockResolvedValueOnce({ closeMatches: [], otherEvents: [3] });
      const { useUnmatchedBridgeTransactions } = await importFresh();
      const { autoMatchBridgeTransaction } = useUnmatchedBridgeTransactions();

      const matched = await autoMatchBridgeTransaction({
        groupIdentifier: 'group-a',
        identifier: 5,
        timeRange: 3600,
        tolerance: '0.01',
      });

      expect(matched).toBe(false);
      expect(spies.matchBridgeTransactions).not.toHaveBeenCalled();
    });
  });

  describe('getBridgeExtraData', () => {
    it('should parse the bridge metadata from the event extra data', async () => {
      const { getBridgeExtraData } = await importFresh();

      expect(getBridgeExtraData({ bridge: { fromChain: 1, toAddress: '0xabc' } })).toEqual({
        fromChain: 1,
        toAddress: '0xabc',
      });
    });

    it('should return undefined for malformed extra data', async () => {
      const { getBridgeExtraData } = await importFresh();

      expect(getBridgeExtraData(null)).toBeUndefined();
      expect(getBridgeExtraData({ bridge: 'nope' })).toBeUndefined();
      expect(getBridgeExtraData({})).toBeUndefined();
    });
  });

  describe('getResolvedBridgeDirection', () => {
    it('should parse the original direction from the matched bridge stamp', async () => {
      const { getResolvedBridgeDirection } = await importFresh();

      expect(getResolvedBridgeDirection({ matchedBridge: { direction: 'deposit', resolution: 'external' } })).toBe('deposit');
      expect(getResolvedBridgeDirection({ matchedBridge: { direction: 'withdrawal', resolution: 'external' } })).toBe('withdrawal');
    });

    it('should return undefined without a valid direction stamp', async () => {
      const { getResolvedBridgeDirection } = await importFresh();

      expect(getResolvedBridgeDirection(null)).toBeUndefined();
      expect(getResolvedBridgeDirection({})).toBeUndefined();
      expect(getResolvedBridgeDirection({ matchedBridge: {} })).toBeUndefined();
      expect(getResolvedBridgeDirection({ matchedBridge: { direction: 'sideways' } })).toBeUndefined();
    });
  });
});
