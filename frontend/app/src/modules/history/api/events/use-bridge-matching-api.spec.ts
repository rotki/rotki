import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBridgeMatchingApi } from '@/modules/history/api/events/use-bridge-matching-api';

const { spies } = vi.hoisted(() => ({
  spies: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    triggerTask: vi.fn(),
  },
}));

vi.mock('@/modules/core/api/rotki-api', () => ({
  api: {
    delete: spies.delete,
    get: spies.get,
    post: spies.post,
    put: spies.put,
  },
}));

vi.mock('@/modules/core/tasks/use-task-api', () => ({
  useTaskApi: (): object => ({ triggerTask: spies.triggerTask }),
}));

describe('use-bridge-matching-api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch unmatched bridge transactions with the only-ignored flag', async () => {
    spies.get.mockResolvedValueOnce(['group-a']);
    const { getUnmatchedBridgeTransactions } = useBridgeMatchingApi();

    await expect(getUnmatchedBridgeTransactions(true)).resolves.toEqual(['group-a']);

    expect(spies.get).toHaveBeenCalledWith('/history/events/match/bridges', {
      params: { only_ignored: true },
    });
  });

  it('should not send params when the only-ignored flag is omitted', async () => {
    spies.get.mockResolvedValueOnce([]);
    const { getUnmatchedBridgeTransactions } = useBridgeMatchingApi();

    await getUnmatchedBridgeTransactions();

    expect(spies.get).toHaveBeenCalledWith('/history/events/match/bridges', {
      params: undefined,
    });
  });

  it('should request bridge match suggestions with the search criteria', async () => {
    spies.post.mockResolvedValueOnce({ closeMatches: [1], otherEvents: [2] });
    const { getBridgeMatches } = useBridgeMatchingApi();

    await expect(getBridgeMatches('group-a', 3600, true, '0.01')).resolves.toEqual({
      closeMatches: [1],
      otherEvents: [2],
    });

    expect(spies.post).toHaveBeenCalledWith('/history/events/match/bridges', {
      bridgeEvent: 'group-a',
      onlyExpectedAssets: true,
      timeRange: 3600,
      tolerance: '0.01',
    });
  });

  it('should link matched events without the external flag', async () => {
    spies.put.mockResolvedValueOnce(true);
    const { matchBridgeTransactions } = useBridgeMatchingApi();

    await matchBridgeTransactions(42, [1, 2]);

    expect(spies.put).toHaveBeenCalledWith('/history/events/match/bridges', {
      bridgeEvent: 42,
      external: false,
      matchedEvents: [1, 2],
    });
  });

  it('should mark a no-match without sending matched events', async () => {
    spies.put.mockResolvedValueOnce(true);
    const { matchBridgeTransactions } = useBridgeMatchingApi();

    await matchBridgeTransactions(42);

    expect(spies.put).toHaveBeenCalledWith('/history/events/match/bridges', {
      bridgeEvent: 42,
      external: false,
    });
  });

  it('should resolve a deposit as external via the external flag', async () => {
    spies.put.mockResolvedValueOnce(true);
    const { matchBridgeTransactions } = useBridgeMatchingApi();

    await matchBridgeTransactions(42, undefined, true);

    expect(spies.put).toHaveBeenCalledWith('/history/events/match/bridges', {
      bridgeEvent: 42,
      external: true,
    });
  });

  it('should unlink a bridge transaction by identifier', async () => {
    spies.delete.mockResolvedValueOnce(true);
    const { unlinkBridgeTransaction } = useBridgeMatchingApi();

    await unlinkBridgeTransaction(7);

    expect(spies.delete).toHaveBeenCalledWith('/history/events/match/bridges', {
      body: { identifier: 7 },
    });
  });

  it('should trigger the bridge matching task', async () => {
    spies.triggerTask.mockResolvedValueOnce({ taskId: 5 });
    const { triggerBridgeMatching } = useBridgeMatchingApi();

    await expect(triggerBridgeMatching()).resolves.toEqual({ taskId: 5 });

    expect(spies.triggerTask).toHaveBeenCalledWith('bridge_matching');
  });
});
