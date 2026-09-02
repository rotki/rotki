import { get } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
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

  it('should treat a failed query as a zero count', async () => {
    listIssues.mockResolvedValue({ error: { message: 'boom' }, ok: false });
    const { baselineTotal, counts, refreshSummary } = useDataIssuesSummary();

    await refreshSummary();

    expect(get(counts)[IssueState.OPEN]).toBe(0);
    expect(get(baselineTotal)).toBe(0);
  });
});
