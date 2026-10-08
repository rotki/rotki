import { bigNumberify } from '@rotki/common';
import { mockUseTaskHandler } from '@test/utils/mocks/task-runner';
import { get } from '@vueuse/core';
import flushPromises from 'flush-promises';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import { HistoricalBalanceDivergenceResponse } from '@/modules/history/balances/types';
import { ActivityKind, ActivityPart, ActivityStatus, makeActivityId } from '@/modules/task-center/core/types';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

const { runTaskMock } = vi.hoisted(() => ({ runTaskMock: vi.fn() }));
const mockFindDivergence = vi.fn();
const mockRequestNavigation = vi.fn();
const mockSetHighlightTarget = vi.fn();

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): object => ({
    getAssetField: (_asset: string, field: string): string => field === 'symbol' ? 'VTLP' : 'Vault position',
  }),
}));

vi.mock('@/modules/core/tasks/use-task-handler', async importOriginal =>
  mockUseTaskHandler(await importOriginal<Record<string, unknown>>(), { runTask: runTaskMock }));

vi.mock('@/modules/balances/api/use-historical-balances-api', () => ({
  useHistoricalBalancesApi: (): object => ({
    findHistoricalBalanceDivergence: mockFindDivergence,
  }),
}));

vi.mock('@/modules/history/events/use-history-event-navigation', () => ({
  HighlightTargetTypes: {
    ACCOUNTING_EVENT: 'accountingEvent',
  },
  useHistoryEventNavigation: (): object => ({
    requestNavigation: mockRequestNavigation,
    setHighlightTarget: mockSetHighlightTarget,
  }),
}));

function boundaryEvent(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    blockNumber: 11,
    difference: '0',
    eventIdentifier: 101,
    groupIdentifier: `1${'a'.repeat(64)}`,
    onchainBalance: '5',
    timestamp: 100,
    trackedBalance: '5',
    txHash: `0x${'a'.repeat(64)}`,
    ...overrides,
  };
}

function divergedResult(): Record<string, unknown> {
  return {
    address: '0xA',
    asset: 'ETH',
    firstDiverged: boundaryEvent({ blockNumber: 12, difference: '0.1', eventIdentifier: 102, groupIdentifier: `1${'b'.repeat(64)}`, onchainBalance: '4.9' }),
    lastMatching: boundaryEvent(),
    location: 'ethereum',
    probes: [],
    status: 'diverged',
    tolerance: '0',
    totalEvents: 2,
  };
}

describe('useBalanceDivergence', () => {
  let useBalanceDivergence: typeof import('./use-balance-divergence').useBalanceDivergence;

  beforeEach(async () => {
    runTaskMock.mockReset();
    mockFindDivergence.mockReset();
    mockFindDivergence.mockResolvedValue({ taskId: 1 });
    mockRequestNavigation.mockReset();
    mockSetHighlightTarget.mockReset();
    ({ useBalanceDivergence } = await import('./use-balance-divergence'));
  });

  it('should run the divergence task and expose the derived boundaries and summary', async () => {
    runTaskMock.mockReturnValue(ok(divergedResult()));
    const divergence = useBalanceDivergence();

    await divergence.find({ address: '0xA', asset: 'ETH', evmChain: 'ethereum' });
    await flushPromises();

    expect(mockFindDivergence).toHaveBeenCalledWith({ address: '0xA', asset: 'ETH', evmChain: 'ethereum' });
    expect(get(divergence.loading)).toBe(false);
    expect(get(divergence.boundaries).map(boundary => boundary.key)).toStrictEqual(['last_matching', 'first_diverged']);
    expect(get(divergence.summary)).toContain('balance_divergence.checked');
    expect(get(divergence.error)).toBeUndefined();
  });

  it('should restore the completed boundaries without running another task', () => {
    const result = HistoricalBalanceDivergenceResponse.parse(divergedResult());
    const divergence = useBalanceDivergence(result);

    expect(get(divergence.boundaries).map(boundary => boundary.event.eventIdentifier)).toEqual([101, 102]);
    expect(get(divergence.summary)).toContain('balance_divergence.checked');
    expect(mockFindDivergence).not.toHaveBeenCalled();
  });

  it('should label the dock activity with the asset symbol', async () => {
    runTaskMock.mockReturnValue(ok(divergedResult()));
    const asset = 'eip155:1/erc721:0x73cD8626b3cD47B009E68380720CFE6679A3Ec3D/182';
    await useBalanceDivergence().find({ address: '0xA', asset, evmChain: 'ethereum' });
    const id = makeActivityId(ActivityKind.HISTORICAL_BALANCES, ActivityPart.DIVERGENCE, asset, '0xA', 'ethereum', 0, 'latest');
    expect(useTaskOrchestrator().snapshot().find(activity => activity.id === id)?.subtitle).toEqual({
      key: 'task_center.activity.historical_balances.divergence',
      params: { asset: 'VTLP' },
      plural: undefined,
    });
  });

  it('should explain a search without checkpoints without showing boundary cards', async () => {
    runTaskMock.mockReturnValue(ok({
      ...divergedResult(),
      firstDiverged: null,
      lastMatching: null,
      status: 'no_checkpoints',
      totalEvents: 0,
    }));
    const divergence = useBalanceDivergence();
    await divergence.find({ address: '0xA', asset: 'ETH', evmChain: 'ethereum' });
    expect(get(divergence.summary)).toBe('balance_divergence.no_checkpoints');
    expect(get(divergence.boundaries)).toEqual([]);
    expect(get(divergence.error)).toBeUndefined();
  });

  it('should record an invalid response as a dock failure and preserve the previous result', async () => {
    const previous = HistoricalBalanceDivergenceResponse.parse(divergedResult());
    const divergence = useBalanceDivergence(previous);
    runTaskMock.mockReturnValue(ok({ status: 'invalid' }));
    await divergence.find({ address: '0xA', asset: 'ETH', evmChain: 'ethereum' });
    await flushPromises();
    const id = makeActivityId(ActivityKind.HISTORICAL_BALANCES, ActivityPart.DIVERGENCE, 'ETH', '0xA', 'ethereum', 0, 'latest');
    const activity = useTaskOrchestrator().snapshot().find(activity => activity.id === id);
    expect(activity?.status).toBe(ActivityStatus.FAILED);
    expect(get(divergence.error)).toBeTruthy();
    expect(get(divergence.result)).toBe(previous);
  });

  it.each([
    TaskFailed({ message: 'boom' }),
    Cancelled({ message: 'cancelled' }),
  ])('should preserve a successful result during and after an unsuccessful re-run: %s', async (failure) => {
    const previous = HistoricalBalanceDivergenceResponse.parse(divergedResult());
    const divergence = useBalanceDivergence(previous);
    let finish = (): void => {};
    runTaskMock.mockImplementationOnce(async () => new Promise((resolve) => {
      finish = (): void => resolve(err(failure));
    }));
    const search = divergence.find({ address: '0xA', asset: 'ETH', evmChain: 'ethereum' });
    await flushPromises();
    try {
      expect(get(divergence.loading)).toBe(true);
      expect(get(divergence.result)).toBe(previous);
      expect(get(divergence.boundaries)).toHaveLength(2);
    }
    finally {
      finish();
      await search;
    }
    expect(get(divergence.result)).toBe(previous);
    expect(get(divergence.loading)).toBe(false);
    expect(get(divergence.error)).toBe(failure._tag === 'TaskFailed' ? 'boom' : undefined);
  });

  it('should not dedup two runs that differ only by tolerance', async () => {
    runTaskMock.mockReturnValue(ok(divergedResult()));
    const divergence = useBalanceDivergence();

    await Promise.all([
      divergence.find({ address: '0xA', asset: 'ETH', evmChain: 'ethereum' }),
      divergence.find({ address: '0xA', asset: 'ETH', evmChain: 'ethereum', tolerance: '5' }),
    ]);
    await flushPromises();

    expect(mockFindDivergence).toHaveBeenCalledTimes(2);
  });

  it('should surface the failure message on an actionable failure', async () => {
    runTaskMock.mockReturnValue(err(TaskFailed({ message: 'boom' })));
    const divergence = useBalanceDivergence();

    await divergence.find({ address: '0xA', asset: 'ETH', evmChain: 'ethereum' });
    await flushPromises();

    expect(get(divergence.error)).toBe('boom');
    expect(get(divergence.boundaries)).toStrictEqual([]);
  });

  it('should not set an error when the task is cancelled', async () => {
    runTaskMock.mockReturnValue(err(Cancelled({ message: 'cancelled' })));
    const divergence = useBalanceDivergence();

    await divergence.find({ address: '0xA', asset: 'ETH', evmChain: 'ethereum' });
    await flushPromises();

    expect(get(divergence.error)).toBeUndefined();
  });

  it('should navigate to a boundary event by highlighting it and requesting navigation', () => {
    const divergence = useBalanceDivergence();

    divergence.navigate({
      blockNumber: 11,
      difference: bigNumberify('0'),
      eventIdentifier: 101,
      groupIdentifier: 'group-1',
      onchainBalance: bigNumberify('5'),
      timestamp: 100,
      trackedBalance: bigNumberify('5'),
      txHash: null,
    }, 'ETH');

    expect(mockSetHighlightTarget).toHaveBeenCalledWith('accountingEvent', {
      groupIdentifier: 'group-1',
      identifier: 101,
    });
    expect(mockRequestNavigation).toHaveBeenCalledWith({
      assetFilter: 'ETH',
      highlightedAccountingEvent: 101,
      targetGroupIdentifier: 'group-1',
    });
  });

  it('should not navigate without a group identifier or asset', () => {
    const divergence = useBalanceDivergence();
    const event = {
      blockNumber: 11,
      difference: bigNumberify('0'),
      eventIdentifier: 101,
      groupIdentifier: null,
      onchainBalance: bigNumberify('5'),
      timestamp: 100,
      trackedBalance: bigNumberify('5'),
      txHash: null,
    };

    divergence.navigate(event, 'ETH');
    divergence.navigate({ ...event, groupIdentifier: 'group-1' }, '');

    expect(mockSetHighlightTarget).not.toHaveBeenCalled();
    expect(mockRequestNavigation).not.toHaveBeenCalled();
  });

  it('should clear a previous result and error', async () => {
    runTaskMock.mockReturnValue(ok(divergedResult()));
    const divergence = useBalanceDivergence();

    await divergence.find({ address: '0xA', asset: 'ETH', evmChain: 'ethereum' });
    await flushPromises();
    expect(get(divergence.boundaries)).toHaveLength(2);

    divergence.clear();

    expect(get(divergence.boundaries)).toStrictEqual([]);
    expect(get(divergence.summary)).toBeUndefined();
    expect(get(divergence.error)).toBeUndefined();
  });
});
