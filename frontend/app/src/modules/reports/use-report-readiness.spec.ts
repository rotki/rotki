import type { DataIssue } from '@/modules/history/data-issues/schemas';
import type { ReportReadiness } from '@/modules/reports/readiness-types';
import { flushPromises, mount } from '@vue/test-utils';
import { get, set } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, ref } from 'vue';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';
import { useReportReadiness } from '@/modules/reports/use-report-readiness';

const spies = vi.hoisted(() => ({
  enabled: true,
  fetchReportReadiness: vi.fn(),
  listIssues: vi.fn(),
}));

vi.mock('@/modules/core/common/feature-flags', () => ({
  isAccountingUpdateEnabled: (): boolean => spies.enabled,
}));

vi.mock('@/modules/reports/use-reports-api', () => ({
  useReportsApi: (): Record<string, unknown> => ({
    fetchReportReadiness: spies.fetchReportReadiness,
  }),
}));

vi.mock('@/modules/history/data-issues/api/use-data-issues-api', () => ({
  useDataIssuesApi: (): Record<string, unknown> => ({
    listIssues: spies.listIssues,
  }),
}));

vi.mock('@/modules/history/data-issues/use-data-issues-auto-reload', () => ({
  useDataIssuesAutoReload: vi.fn(),
}));

function createIssue(overrides: Partial<DataIssue> = {}): DataIssue {
  return {
    asset: 'ETH',
    autoRemediationAttempts: [],
    createdAt: 1710000100,
    eventIdentifier: 1,
    groupIdentifier: 'g-1',
    id: 1,
    kind: IssueKind.MISSING_PRICE,
    location: 'ethereum',
    locationLabel: null,
    payload: { amount: '1', direction: 'spend', eventIdentifier: 1, groupIdentifier: 'g-1', toAsset: 'USD' },
    protocol: null,
    resolvedAt: null,
    severity: IssueSeverity.WARNING,
    state: IssueState.OPEN,
    suggestedActions: [],
    tsEnd: 1710000000000,
    tsStart: 1710000000000,
    ...overrides,
  };
}

function mountComposable(startTs?: number, endTs?: number): ReturnType<typeof useReportReadiness> {
  let result!: ReturnType<typeof useReportReadiness>;
  const start = ref(startTs);
  const end = ref(endTs);
  const Host = defineComponent({
    setup(): () => null {
      result = useReportReadiness({ endTs: end, startTs: start });
      return () => null;
    },
  });
  mount(Host, { global: { plugins: [createPinia()] } });
  return result;
}

describe('useReportReadiness', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    spies.enabled = true;
  });

  it('should skip API requests when the accounting update feature flag is off', async () => {
    spies.enabled = false;
    mountComposable(100, 200);
    await flushPromises();

    expect(spies.fetchReportReadiness).not.toHaveBeenCalled();
    expect(spies.listIssues).not.toHaveBeenCalled();
  });

  it('should fetch readiness on mount and lazily load grouped open issues when expanded', async () => {
    const readiness: ReportReadiness = {
      evaluatedThroughTs: 200000,
      numUnpricedEvents: 1,
      numUnruledEvents: 3,
      openIssuesByKind: { [IssueKind.MISSING_COST_BASIS]: 1, [IssueKind.MISSING_PRICE]: 2 },
      openIssuesCount: 3,
      ready: false,
      stale: false,
    };
    spies.fetchReportReadiness.mockResolvedValue(readiness);
    spies.listIssues.mockResolvedValue(ok({
      data: [
        createIssue({ id: 1, kind: IssueKind.MISSING_PRICE, payload: { amount: '2', direction: 'spend', eventIdentifier: 1, groupIdentifier: 'g', toAsset: 'USD' } }),
        createIssue({ id: 2, kind: IssueKind.MISSING_PRICE, payload: { amount: '10', direction: 'spend', eventIdentifier: 2, groupIdentifier: 'g', toAsset: 'USD' } }),
        createIssue({ id: 3, kind: IssueKind.MISSING_COST_BASIS, payload: { coveredAmount: '0', eventIdentifier: 3, fallbackBasis: '0', groupIdentifier: 'g', requestedAmount: '5', uncoveredAmount: '5' } }),
      ],
      found: 3,
      limit: 100,
      total: 3,
    }));

    const state = mountComposable(100, 200);
    await flushPromises();

    expect(spies.fetchReportReadiness).toHaveBeenCalledWith({ fromTimestamp: 100, toTimestamp: 200 });
    expect(spies.listIssues).not.toHaveBeenCalled();

    set(state.modelExpanded, true);
    await flushPromises();

    expect(spies.listIssues).toHaveBeenCalledWith(expect.objectContaining({
      toTimestamp: 200000,
    }));
    const groups = get(state.groupedIssues);
    expect(groups.map(group => group.kind)).toStrictEqual([IssueKind.MISSING_PRICE, IssueKind.MISSING_COST_BASIS]);
    // Higher impact item (amount 10) sorted before smaller item (amount 2)
    expect(groups[0]?.issues.map(issue => issue.id)).toStrictEqual([2, 1]);
  });

  it('should convert endTs seconds to milliseconds when evaluatedThroughTs is null', async () => {
    spies.fetchReportReadiness.mockResolvedValue({
      evaluatedThroughTs: null,
      numUnpricedEvents: 0,
      numUnruledEvents: 0,
      openIssuesByKind: { [IssueKind.MISSING_PRICE]: 1 },
      openIssuesCount: 1,
      ready: false,
      stale: false,
    });
    spies.listIssues.mockResolvedValue(ok({
      data: [createIssue({ id: 1 })],
      found: 1,
      limit: 100,
      total: 1,
    }));

    const state = mountComposable(100, 1700000000);
    await flushPromises();
    set(state.modelExpanded, true);
    await flushPromises();

    expect(spies.listIssues).toHaveBeenCalledWith(expect.objectContaining({
      toTimestamp: 1700000000000,
    }));
  });
});
