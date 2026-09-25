import { get } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RequestCancelledError } from '@/modules/core/api/request-queue/errors';
import { IssueState } from '@/modules/history/data-issues/constants';
import { useDataIssuesSummary } from '@/modules/history/data-issues/use-data-issues-summary';

const listIssues = vi.fn();

vi.mock('@/modules/history/data-issues/api/use-data-issues-api', () => ({
  useDataIssuesApi: (): Record<string, unknown> => ({
    listIssues,
  }),
}));

const FOUND_PER_STATE: Record<string, number> = {
  [IssueState.OPEN]: 3,
  [IssueState.AUTO_REMEDIATING]: 2,
  [IssueState.UNRESOLVED]: 5,
};
const BASELINE = 20;

describe('useDataIssuesSummary', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    listIssues.mockImplementation(async ({ state }: { state: IssueState[] }) => {
      const found = state.length === Object.values(IssueState).length
        ? BASELINE
        : FOUND_PER_STATE[state[0]] ?? 0;
      return { ok: true, value: { found } };
    });
  });

  it('should aggregate per-state counts and the baseline total into the store', async () => {
    const { baselineTotal, counts, refreshSummary } = useDataIssuesSummary();

    await refreshSummary();

    expect(get(counts)[IssueState.OPEN]).toBe(3);
    expect(get(counts)[IssueState.AUTO_REMEDIATING]).toBe(2);
    expect(get(counts)[IssueState.UNRESOLVED]).toBe(5);
    expect(get(counts)[IssueState.RESOLVED]).toBe(0);
    expect(get(counts)[IssueState.DISMISSED]).toBe(0);
    expect(get(baselineTotal)).toBe(BASELINE);
  });

  it('should expose actionableCount as open + unresolved only', async () => {
    const { actionableCount, refreshSummary } = useDataIssuesSummary();

    await refreshSummary();

    expect(get(actionableCount)).toBe(8);
  });

  it('should keep the previous counts and mark the summary failed when a query fails', async () => {
    const { baselineTotal, counts, refreshSummary, summaryFailed } = useDataIssuesSummary();
    await refreshSummary();

    listIssues.mockResolvedValueOnce({ error: { cause: new TypeError('fetch failed'), message: 'fetch failed', type: 'network' }, ok: false });
    await refreshSummary();

    expect(get(counts)[IssueState.OPEN]).toBe(3);
    expect(get(baselineTotal)).toBe(BASELINE);
    expect(get(summaryFailed)).toBe(true);
  });

  it('should leave the summary untouched when a query is cancelled', async () => {
    const { counts, refreshSummary, summaryFailed } = useDataIssuesSummary();
    await refreshSummary();

    listIssues.mockResolvedValueOnce({ error: { cause: new RequestCancelledError('All requests cancelled'), message: 'All requests cancelled', type: 'network' }, ok: false });
    await refreshSummary();

    expect(get(counts)[IssueState.OPEN]).toBe(3);
    expect(get(summaryFailed)).toBe(false);
  });

  it('should clear the failure once a refresh succeeds', async () => {
    const { refreshSummary, summaryFailed } = useDataIssuesSummary();
    listIssues.mockResolvedValueOnce({ error: { cause: new TypeError('fetch failed'), message: 'fetch failed', type: 'network' }, ok: false });
    await refreshSummary();
    expect(get(summaryFailed)).toBe(true);

    await refreshSummary();

    expect(get(summaryFailed)).toBe(false);
  });
});
