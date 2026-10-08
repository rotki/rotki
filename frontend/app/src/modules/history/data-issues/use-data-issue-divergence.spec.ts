import type { HistoricalBalanceDivergenceResponse } from '@/modules/history/balances/types';
import type { DivergenceBoundaryEvent, useBalanceDivergence } from '@/modules/history/balances/use-balance-divergence';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import type { PinnedNames, PinnedPanelProps } from '@/modules/session/types';
import { createMock } from '@test/utils/create-mock';
import { flushPromises } from '@vue/test-utils';
import { get, set } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type MaybeRefOrGetter, ref, toValue } from 'vue';
import { IssueKind } from '@/modules/history/data-issues/constants';
import { useDataIssueDivergence } from '@/modules/history/data-issues/use-data-issue-divergence';

const { captureInitialResult, divergence, enabled, nodes, fetchNodes, pin } = await vi.hoisted(async () => {
  const { computed, ref } = await import('vue');
  const { vi } = await import('vitest');
  return {
    captureInitialResult: vi.fn<(initial: MaybeRefOrGetter<HistoricalBalanceDivergenceResponse | undefined>) => void>(),
    divergence: {
      boundaries: computed<DivergenceBoundaryEvent[]>(() => []),
      clear: vi.fn<() => void>(),
      error: ref<string>(),
      find: vi.fn<ReturnType<typeof useBalanceDivergence>['find']>(),
      loading: ref<boolean>(false),
      navigate: vi.fn<ReturnType<typeof useBalanceDivergence>['navigate']>(),
      result: ref<HistoricalBalanceDivergenceResponse>(),
      summary: computed<string | undefined>(() => undefined),
    } satisfies ReturnType<typeof useBalanceDivergence>,
    enabled: { value: true },
    fetchNodes: vi.fn<(chain: string) => void>(),
    nodes: { archive: true },
    pin: vi.fn<(props: PinnedPanelProps[typeof PinnedNames.BALANCE_DIVERGENCE]) => void>(),
  };
});

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

vi.mock('@/modules/history/balances/use-balance-divergence', () => ({
  useBalanceDivergence: (
    initial: MaybeRefOrGetter<HistoricalBalanceDivergenceResponse | undefined>,
  ): ReturnType<typeof useBalanceDivergence> => {
    captureInitialResult(initial);
    return divergence;
  },
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

let scope = effectScope();

function useDiagnostic(issue: DataIssue): ReturnType<typeof useDataIssueDivergence> {
  const result = scope.run(() => useDataIssueDivergence(() => issue));
  assert(result);
  return result;
}

describe('useDataIssueDivergence bounded wallet search', () => {
  beforeEach(() => {
    scope = effectScope();
    setActivePinia(createPinia());
    vi.clearAllMocks();
    divergence.find.mockReset();
    enabled.value = true;
    nodes.archive = true;
    set(divergence.loading, false);
    set(divergence.result, undefined);
  });

  afterEach(() => scope.stop());

  it.each([IssueKind.NEGATIVE_BALANCE, IssueKind.CURRENT_BALANCE_MISMATCH])('should search %s through its timestamp in milliseconds with no manual selection', async (kind) => {
    const diagnostic = useDiagnostic(makeIssue({ kind }));
    await flushPromises();
    expect(fetchNodes).toHaveBeenCalledWith('eth');
    expect(get(diagnostic.canSearch)).toBe(true);
    await diagnostic.search();
    expect(divergence.find).toHaveBeenCalledWith({
      address: '0x0000000000000000000000000000000000000001',
      asset: 'ETH',
      evmChain: 'ethereum',
      toTimestamp: 1710000000123,
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
    expect(divergence.find).not.toHaveBeenCalled();
    expect(fetchNodes).not.toHaveBeenCalled();
  });

  it('should hide the diagnostic when the accounting update is disabled', async () => {
    enabled.value = false;
    const diagnostic = useDiagnostic(makeIssue());
    await flushPromises();
    expect(get(diagnostic.available)).toBe(false);
    await diagnostic.search();
    expect(divergence.find).not.toHaveBeenCalled();
  });

  it('should block queries without an archive node', async () => {
    nodes.archive = false;
    const diagnostic = useDiagnostic(makeIssue());
    await flushPromises();
    expect(get(diagnostic.available)).toBe(true);
    expect(get(diagnostic.missingArchive)).toBe(true);
    expect(get(diagnostic.canSearch)).toBe(false);
    await diagnostic.search();
    expect(divergence.find).not.toHaveBeenCalled();
  });

  it('should prevent duplicate searches while a diagnostic is running', async () => {
    const diagnostic = useDiagnostic(makeIssue());
    await flushPromises();
    set(divergence.loading, true);
    expect(get(diagnostic.canSearch)).toBe(false);
    await diagnostic.search();
    expect(divergence.find).not.toHaveBeenCalled();
  });

  it('should pin the issue before navigating to a checkpoint', () => {
    const issue = makeIssue();
    const diagnostic = useDiagnostic(issue);
    const boundary = createMock<DivergenceBoundaryEvent>({
      event: createMock<DivergenceBoundaryEvent['event']>({ eventIdentifier: 123, groupIdentifier: 'group-1' }),
    });

    diagnostic.view(boundary);

    expect(pin).toHaveBeenCalledWith({ issue });
    expect(divergence.navigate).toHaveBeenCalledWith(boundary.event, 'ETH');
    expect(pin.mock.invocationCallOrder[0]).toBeLessThan(divergence.navigate.mock.invocationCallOrder[0]);
  });

  it('should keep a completed result for a later view of the same issue', async () => {
    const result = createMock<HistoricalBalanceDivergenceResponse>({ status: 'diverged' });
    divergence.find.mockImplementation(async () => {
      set(divergence.result, result);
    });
    const first = useDiagnostic(makeIssue());
    await flushPromises();
    await first.search();
    set(divergence.result, undefined);

    useDiagnostic(makeIssue());
    expect(toValue(captureInitialResult.mock.lastCall?.[0])).toBe(result);
    useDiagnostic(makeIssue({ tsEnd: 1720000000000 }));
    expect(toValue(captureInitialResult.mock.lastCall?.[0])).toBeUndefined();
  });

  it('should show a search still running for the issue when it is viewed again', async () => {
    let finish = (): void => {};
    divergence.find.mockImplementation(async () => new Promise<void>((resolve) => {
      finish = resolve;
    }));
    const first = useDiagnostic(makeIssue());
    await flushPromises();
    const running = first.search();

    const second = useDiagnostic(makeIssue());
    await flushPromises();
    expect(get(second.loading)).toBe(true);
    expect(get(second.canSearch)).toBe(false);

    finish();
    await running;
    expect(get(second.loading)).toBe(false);
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
    expect(divergence.find).toHaveBeenCalledWith(expect.objectContaining({
      asset: 'other-token',
      toTimestamp: 1700000000000,
    }));
  });
});
