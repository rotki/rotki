import type { z } from 'zod';
import type { useHistoricalBalancesApi } from '@/modules/balances/api/use-historical-balances-api';
import type { HistoricalBalanceDivergenceResponse } from '@/modules/history/balances/types';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import type { PinnedNames, PinnedPanelProps } from '@/modules/session/types';
import { createMock } from '@test/utils/create-mock';
import { mockUseTaskHandler } from '@test/utils/mocks/task-runner';
import { flushPromises } from '@vue/test-utils';
import { get, set } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { err, ok, type Result } from 'plainfp/result';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, ref } from 'vue';
import { Cancelled, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { IssueKind } from '@/modules/history/data-issues/constants';
import { useDataIssueDivergence } from '@/modules/history/data-issues/use-data-issue-divergence';

const { enabled, nodes, fetchNodes, findDivergence, runTask, pin, requestNavigation, setHighlightTarget } = vi.hoisted(() => ({
  enabled: { value: true },
  fetchNodes: vi.fn<(chain: string) => void>(),
  findDivergence: vi.fn<ReturnType<typeof useHistoricalBalancesApi>['findHistoricalBalanceDivergence']>(),
  nodes: { archive: true },
  pin: vi.fn<(props: PinnedPanelProps[typeof PinnedNames.BALANCE_DIVERGENCE]) => void>(),
  requestNavigation: vi.fn<(request: object) => void>(),
  runTask: vi.fn<() => Promise<Result<z.input<typeof HistoricalBalanceDivergenceResponse>, TaskError>>>(),
  setHighlightTarget: vi.fn<(type: string, target: object) => void>(),
}));

vi.mock('@/modules/core/tasks/use-task-handler', async importOriginal =>
  mockUseTaskHandler(await importOriginal<Record<string, unknown>>(), { runTask }));

vi.mock('@/modules/balances/api/use-historical-balances-api', () => ({
  useHistoricalBalancesApi: (): object => ({ findHistoricalBalanceDivergence: findDivergence }),
}));

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): object => ({ getAssetField: (): string => 'ETH' }),
}));

vi.mock('@/modules/history/events/use-history-event-navigation', () => ({
  HighlightTargetTypes: { ACCOUNTING_EVENT: 'accountingEvent' },
  useHistoryEventNavigation: (): object => ({ requestNavigation, setHighlightTarget }),
}));

vi.mock('@/modules/shell/pinned/use-pinned-panel', () => ({
  usePinnedPanel: (): object => ({ pin }),
}));

vi.mock('@/modules/core/common/feature-flags', () => ({
  isAccountingUpdateEnabled: (): boolean => enabled.value,
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({
    getChainName: (chain: string): string => chain === 'eth' ? 'Ethereum' : chain,
    getEvmChainName: (chain: string): string | undefined => chain === 'eth' ? 'ethereum' : undefined,
    matchChain: (location: string): string | undefined => location === 'ethereum' ? 'eth' : undefined,
  }),
}));

vi.mock('@/modules/settings/api/use-evm-nodes-api', () => ({
  useEvmNodesApi: (chain: string): object => ({
    fetchEvmNodes: async (): Promise<{ isArchive: boolean }[]> => {
      fetchNodes(chain);
      return [{ isArchive: nodes.archive }];
    },
  }),
}));

function makeIssue(overrides: Partial<DataIssue> = {}): DataIssue {
  return createMock<DataIssue>({
    asset: 'ETH',
    kind: IssueKind.NEGATIVE_BALANCE,
    location: 'ethereum',
    locationLabel: '0x0000000000000000000000000000000000000001',
    protocol: null,
    id: 7,
    tsEnd: 1710000000123,
    ...overrides,
  });
}

function makeResult(overrides: Partial<z.input<typeof HistoricalBalanceDivergenceResponse>> = {}): z.input<typeof HistoricalBalanceDivergenceResponse> {
  return {
    address: '0x0000000000000000000000000000000000000001',
    asset: 'ETH',
    firstDiverged: {
      blockNumber: 42,
      difference: '1',
      eventIdentifier: 123,
      groupIdentifier: 'group-1',
      onchainBalance: '3',
      timestamp: 1710000000,
      trackedBalance: '2',
      txHash: null,
    },
    lastMatching: null,
    location: 'ethereum',
    probes: [],
    status: 'diverged_from_start',
    tolerance: '0',
    totalEvents: 1,
    ...overrides,
  };
}

let scope = effectScope();

function useDiagnostic(issue: DataIssue): ReturnType<typeof useDataIssueDivergence> {
  const result = scope.run(() => useDataIssueDivergence(() => issue));
  assert(result);
  return result;
}

describe('useDataIssueDivergence bounded wallet search with independent view instances', () => {
  beforeEach(() => {
    scope = effectScope();
    setActivePinia(createPinia());
    vi.clearAllMocks();
    findDivergence.mockResolvedValue({ taskId: 1 });
    runTask.mockReset();
    runTask.mockResolvedValue(ok(makeResult()));
    enabled.value = true;
    nodes.archive = true;
  });

  afterEach(() => scope.stop());

  it.each([IssueKind.NEGATIVE_BALANCE, IssueKind.CURRENT_BALANCE_MISMATCH])('should search %s through its timestamp in seconds with no manual selection', async (kind) => {
    const diagnostic = useDiagnostic(makeIssue({ kind }));
    await flushPromises();
    expect(fetchNodes).toHaveBeenCalledWith('eth');
    expect(get(diagnostic.canSearch)).toBe(true);
    await diagnostic.search();
    expect(findDivergence).toHaveBeenCalledWith({
      address: '0x0000000000000000000000000000000000000001',
      asset: 'ETH',
      evmChain: 'ethereum',
      toTimestamp: 1710000000,
    });
  });

  it.each([
    { protocol: 'aave-v3' },
    { location: 'kraken' },
    { locationLabel: null },
    { asset: null },
    { kind: IssueKind.UNMATCHED_BRIDGE },
    { kind: IssueKind.REBASING_TOKEN },
  ] satisfies Partial<DataIssue>[])('should not offer archive wallet diagnosis for an unsupported issue %s', async (overrides) => {
    const diagnostic = useDiagnostic(makeIssue(overrides));
    await flushPromises();
    expect(get(diagnostic.available)).toBe(false);
    await diagnostic.search();
    expect(findDivergence).not.toHaveBeenCalled();
    expect(fetchNodes).not.toHaveBeenCalled();
  });

  it('should hide the diagnostic when the accounting update is disabled', async () => {
    enabled.value = false;
    const diagnostic = useDiagnostic(makeIssue());
    await flushPromises();
    expect(get(diagnostic.available)).toBe(false);
    await diagnostic.search();
    expect(findDivergence).not.toHaveBeenCalled();
  });

  it('should block queries without an archive node', async () => {
    nodes.archive = false;
    const diagnostic = useDiagnostic(makeIssue());
    await flushPromises();
    expect(get(diagnostic.available)).toBe(true);
    expect(get(diagnostic.missingArchive)).toBe(true);
    expect(get(diagnostic.canSearch)).toBe(false);
    await diagnostic.search();
    expect(findDivergence).not.toHaveBeenCalled();
  });

  it('should prevent duplicate searches and share running state with a later view', async () => {
    let finish = (): void => {};
    runTask.mockImplementationOnce(async () => new Promise((resolve) => {
      finish = (): void => resolve(ok(makeResult()));
    }));
    const first = useDiagnostic(makeIssue());
    await flushPromises();
    const search = first.search();
    const second = useDiagnostic(makeIssue());
    await flushPromises();
    try {
      expect(get(first.loading)).toBe(true);
      expect(get(second.loading)).toBe(true);
      expect(get(second.canSearch)).toBe(false);
      await second.search();
      expect(findDivergence).toHaveBeenCalledOnce();
    }
    finally {
      finish();
      await search;
    }
    expect(get(second.loading)).toBe(false);
  });

  it('should pin the issue before navigating to a checkpoint', async () => {
    const issue = makeIssue();
    const diagnostic = useDiagnostic(issue);
    await flushPromises();
    await diagnostic.search();
    const boundary = get(diagnostic.boundaries)[0];
    assert(boundary);
    diagnostic.view(boundary);
    expect(pin).toHaveBeenCalledWith({ issue });
    expect(setHighlightTarget).toHaveBeenCalledWith('accountingEvent', { groupIdentifier: 'group-1', identifier: 123 });
    expect(requestNavigation).toHaveBeenCalledWith({ assetFilter: 'ETH', highlightedAccountingEvent: 123, targetGroupIdentifier: 'group-1' });
    expect(pin.mock.invocationCallOrder[0]).toBeLessThan(requestNavigation.mock.invocationCallOrder[0]);
  });

  it('should keep completed boundaries for a later view of the same issue', async () => {
    const first = useDiagnostic(makeIssue());
    await flushPromises();
    await first.search();
    const previous = get(first.boundaries);
    expect(previous).toHaveLength(1);
    scope.stop();
    scope = effectScope();
    expect(get(useDiagnostic(makeIssue()).boundaries)).toEqual(previous);
    expect(get(useDiagnostic(makeIssue({ tsEnd: 1720000000000 })).boundaries)).toEqual([]);
    expect(findDivergence).toHaveBeenCalledOnce();
  });

  it.each([TaskFailed({ message: 'Archive request failed' }), Cancelled({ message: 'cancelled' })])('should preserve successful boundaries after a re-run ends with %s across reopened and pinned views', async (failure) => {
    const first = useDiagnostic(makeIssue());
    await flushPromises();
    await first.search();
    const previous = get(first.boundaries);
    expect(previous).toHaveLength(1);
    const pinned = useDiagnostic(makeIssue());
    await flushPromises();
    runTask.mockResolvedValueOnce(err(failure));
    await first.search();
    await flushPromises();
    const expectedError = failure._tag === 'TaskFailed' ? 'Archive request failed' : undefined;
    expect(get(first.boundaries)).toEqual(previous);
    expect(get(pinned.boundaries)).toEqual(previous);
    expect(get(pinned.error)).toBe(expectedError);
    scope.stop();
    scope = effectScope();
    const reopened = useDiagnostic(makeIssue());
    expect(get(reopened.boundaries)).toEqual(previous);
    expect(get(reopened.error)).toBe(expectedError);
    expect(get(useDiagnostic(makeIssue({ tsEnd: 1720000000000 })).error)).toBeUndefined();
    await flushPromises();
    runTask.mockResolvedValueOnce(ok(makeResult({ firstDiverged: null, status: 'no_divergence' })));
    await reopened.search();
    expect(get(reopened.boundaries)).toEqual([]);
    expect(get(reopened.error)).toBeUndefined();
    expect(get(reopened.status)).toBe('no_divergence');
  });

  it('should explain an issue with no earlier checkpoint and retain its completed status for another view', async () => {
    runTask.mockResolvedValueOnce(ok(makeResult({ firstDiverged: null, status: 'no_checkpoints', totalEvents: 0 })));
    const diagnostic = useDiagnostic(makeIssue());
    await flushPromises();
    await diagnostic.search();
    expect(get(diagnostic.status)).toBe('no_checkpoints');
    expect(get(diagnostic.summary)).toBe('balance_divergence.no_checkpoints');
    expect(get(diagnostic.boundaries)).toEqual([]);
    expect(get(diagnostic.error)).toBeUndefined();
    const reopened = useDiagnostic(makeIssue());
    expect(get(reopened.status)).toBe('no_checkpoints');
    expect(get(reopened.summary)).toBe('balance_divergence.no_checkpoints');
    expect(findDivergence).toHaveBeenCalledOnce();
  });

  it('should name the chain for display', () => {
    expect(get(useDiagnostic(makeIssue()).chainName)).toBe('Ethereum');
  });

  it('should use the current issue scope when the issue changes', async () => {
    const issue = ref<DataIssue>(makeIssue());
    const diagnostic = scope.run(() => useDataIssueDivergence(issue));
    assert(diagnostic);
    await flushPromises();
    set(issue, makeIssue({ asset: 'other-token', tsEnd: 1700000000000 }));
    await diagnostic.search();
    expect(findDivergence).toHaveBeenCalledWith(expect.objectContaining({ asset: 'other-token', toTimestamp: 1700000000 }));
  });
});
