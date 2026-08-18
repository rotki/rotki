import type { DataIssue } from '@/modules/history/data-issues/schemas';
import type { Filters } from '@/modules/history/data-issues/use-data-issues-filter';
import { get, set } from '@vueuse/core';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';
import { PANEL_PAGE_SIZE } from '@/modules/history/data-issues/data-issues-panel-utils';
import { useDataIssuesPanelList } from '@/modules/history/data-issues/use-data-issues-panel-list';

const fetchData = vi.fn();
const refreshSummary = vi.fn();

vi.mock('@/modules/history/data-issues/use-data-issues', () => ({
  useDataIssues: (): Record<string, unknown> => ({ fetchData }),
}));

vi.mock('@/modules/history/data-issues/use-data-issues-summary', () => ({
  useDataIssuesSummary: (): Record<string, unknown> => ({ refreshSummary }),
}));

function createIssue(overrides: Partial<DataIssue> = {}): DataIssue {
  return {
    asset: 'ETH',
    autoRemediationAttempts: [],
    createdAt: 1710000100,
    groupIdentifier: null,
    id: 1,
    kind: IssueKind.NEGATIVE_BALANCE,
    location: 'ethereum',
    locationLabel: '0x0000000000000000000000000000000000000001',
    payload: {},
    protocol: null,
    resolvedAt: null,
    severity: IssueSeverity.WARNING,
    state: IssueState.OPEN,
    tsEnd: 1710000000,
    tsStart: 1710000000,
    ...overrides,
  };
}

/** A page of `count` issues out of `found` total, with ids offset so pages differ. */
function page(count: number, found: number, startId = 1): { data: DataIssue[]; found: number; limit: number; total: number } {
  return {
    data: Array.from({ length: count }, (_, index) => createIssue({ id: startId + index })),
    found,
    limit: PANEL_PAGE_SIZE,
    total: found,
  };
}

describe('useDataIssuesPanelList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    refreshSummary.mockResolvedValue(undefined);
  });

  it('should start empty before anything is loaded', () => {
    const { isEmpty, rows } = useDataIssuesPanelList(ref<Filters>({}));

    expect(get(rows)).toStrictEqual([]);
    expect(get(isEmpty)).toBe(true);
  });

  it('should replace the list on refresh', async () => {
    fetchData.mockResolvedValueOnce(page(2, 2));
    const { isEmpty, refreshList, rows } = useDataIssuesPanelList(ref<Filters>({}));

    await refreshList();

    expect(get(rows)).toHaveLength(2);
    expect(get(isEmpty)).toBe(false);
  });

  it('should request the current filters', async () => {
    const filters = ref<Filters>({ asset: 'BTC' });
    fetchData.mockResolvedValueOnce(page(1, 1));
    const { refreshList } = useDataIssuesPanelList(filters);

    await refreshList();

    expect(fetchData).toHaveBeenCalledWith(expect.objectContaining({ asset: 'BTC', offset: 0 }));
  });

  it('should read the filters at request time, not at construction', async () => {
    const filters = ref<Filters>({ asset: 'BTC' });
    fetchData.mockResolvedValue(page(1, 1));
    const { refreshList } = useDataIssuesPanelList(filters);

    set(filters, { asset: 'ETH' });
    await refreshList();

    expect(fetchData).toHaveBeenLastCalledWith(expect.objectContaining({ asset: 'ETH' }));
  });

  it('should append the next page and advance the offset', async () => {
    fetchData.mockResolvedValueOnce(page(PANEL_PAGE_SIZE, 40));
    const { loadMore, refreshList, rows } = useDataIssuesPanelList(ref<Filters>({}));
    await refreshList();

    fetchData.mockResolvedValueOnce(page(15, 40, 100));
    await loadMore();

    expect(fetchData).toHaveBeenLastCalledWith(expect.objectContaining({ offset: PANEL_PAGE_SIZE }));
    expect(get(rows)).toHaveLength(40);
  });

  it('should not fetch more once everything is loaded', async () => {
    fetchData.mockResolvedValueOnce(page(2, 2));
    const { loadMore, refreshList } = useDataIssuesPanelList(ref<Filters>({}));
    await refreshList();
    fetchData.mockClear();

    await loadMore();

    expect(fetchData).not.toHaveBeenCalled();
  });

  it('should reset the offset back to the first page on refresh', async () => {
    fetchData.mockResolvedValueOnce(page(PANEL_PAGE_SIZE, 40));
    const { loadMore, refreshList } = useDataIssuesPanelList(ref<Filters>({}));
    await refreshList();
    fetchData.mockResolvedValueOnce(page(15, 40, 100));
    await loadMore();

    fetchData.mockResolvedValueOnce(page(PANEL_PAGE_SIZE, 40));
    await refreshList();

    expect(fetchData).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 0 }));
  });

  it('should ignore an overlapping loadMore so a scroll burst cannot double-fetch', async () => {
    fetchData.mockResolvedValueOnce(page(PANEL_PAGE_SIZE, 40));
    const { loadMore, refreshList } = useDataIssuesPanelList(ref<Filters>({}));
    await refreshList();

    fetchData.mockClear();
    fetchData.mockResolvedValue(page(15, 40, 100));
    await Promise.all([loadMore(), loadMore()]);

    expect(fetchData).toHaveBeenCalledOnce();
  });

  it('should expose the loading flag only while the first page is in flight', async () => {
    fetchData.mockResolvedValueOnce(page(1, 1));
    const { loading, refreshList } = useDataIssuesPanelList(ref<Filters>({}));

    const pending = refreshList();
    expect(get(loading)).toBe(true);
    await pending;

    expect(get(loading)).toBe(false);
  });

  it('should mark a page append with loadingMore, leaving loading untouched', async () => {
    fetchData.mockResolvedValueOnce(page(PANEL_PAGE_SIZE, 40));
    const { loading, loadingMore, loadMore, refreshList } = useDataIssuesPanelList(ref<Filters>({}));
    await refreshList();

    fetchData.mockResolvedValueOnce(page(15, 40, 100));
    const pending = loadMore();
    expect(get(loadingMore)).toBe(true);
    expect(get(loading)).toBe(false);
    await pending;

    expect(get(loadingMore)).toBe(false);
  });

  it('should clear the loading flag when the request rejects', async () => {
    fetchData.mockRejectedValueOnce(new Error('boom'));
    const { loading, refreshList } = useDataIssuesPanelList(ref<Filters>({}));

    await expect(refreshList()).rejects.toThrow('boom');

    expect(get(loading)).toBe(false);
  });

  it('should report a remediating row so the caller can start polling', async () => {
    fetchData.mockResolvedValueOnce({
      ...page(1, 1),
      data: [createIssue({ state: IssueState.AUTO_REMEDIATING })],
    });
    const { hasRemediatingRows, refreshList } = useDataIssuesPanelList(ref<Filters>({}));

    await refreshList();

    expect(get(hasRemediatingRows)).toBe(true);
  });

  it('should report no remediating rows when every issue is settled', async () => {
    fetchData.mockResolvedValueOnce({
      ...page(1, 1),
      data: [createIssue({ state: IssueState.OPEN })],
    });
    const { hasRemediatingRows, refreshList } = useDataIssuesPanelList(ref<Filters>({}));

    await refreshList();

    expect(get(hasRemediatingRows)).toBe(false);
  });

  it('should describe each row so the card does not have to', async () => {
    fetchData.mockResolvedValueOnce(page(1, 1));
    const { refreshList, rows } = useDataIssuesPanelList(ref<Filters>({}));

    await refreshList();

    const [row] = get(rows);
    expect(row.issue.id).toBe(1);
    expect(row.description.messageKey).toBeTruthy();
  });

  it('should refresh the list and the badge summary together', async () => {
    fetchData.mockResolvedValueOnce(page(1, 1));
    const { reloadAll } = useDataIssuesPanelList(ref<Filters>({}));

    await reloadAll();

    expect(fetchData).toHaveBeenCalledOnce();
    expect(refreshSummary).toHaveBeenCalledOnce();
  });
});
