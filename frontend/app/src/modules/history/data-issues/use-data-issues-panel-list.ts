import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import type { IssueDescription } from '@/modules/history/data-issues/types';
import type { Filters } from '@/modules/history/data-issues/use-data-issues-filter';
import { IssueState } from '@/modules/history/data-issues/constants';
import { buildPanelPayload, PANEL_PAGE_SIZE } from '@/modules/history/data-issues/data-issues-panel-utils';
import { describeIssue, relatedEventRoute } from '@/modules/history/data-issues/transforms';
import { useDataIssues } from '@/modules/history/data-issues/use-data-issues';
import { useDataIssuesSummary } from '@/modules/history/data-issues/use-data-issues-summary';

/** One rendered card: the issue plus everything derived from it for display. */
export interface PanelRow {
  issue: DataIssue;
  description: IssueDescription;
  eventRoute: RouteLocationRaw | undefined;
}

interface UseDataIssuesPanelListReturn {
  loading: Readonly<Ref<boolean>>;
  loadingMore: Readonly<Ref<boolean>>;
  rows: ComputedRef<PanelRow[]>;
  isEmpty: ComputedRef<boolean>;
  hasRemediatingRows: ComputedRef<boolean>;
  refreshList: () => Promise<void>;
  loadMore: () => Promise<void>;
  reloadAll: () => Promise<void>;
}

/**
 * The panel's paged issue list: one page at a time, appending as the user scrolls.
 * `reloadAll` refreshes the list and the badge summary together, so every caller
 * that changes an issue keeps both in step from a single place.
 */
export function useDataIssuesPanelList(filters: MaybeRefOrGetter<Filters>): UseDataIssuesPanelListReturn {
  const { fetchData } = useDataIssues();
  const { refreshSummary } = useDataIssuesSummary();

  const issues = ref<DataIssue[]>([]);
  const loading = shallowRef<boolean>(false);
  const loadingMore = shallowRef<boolean>(false);
  const offset = shallowRef<number>(0);
  const total = shallowRef<number>(0);

  const canLoadMore = computed<boolean>(() => get(issues).length < get(total));
  const isEmpty = computed<boolean>(() => get(issues).length === 0);

  const hasRemediatingRows = computed<boolean>(() =>
    get(issues).some(issue => issue.state === IssueState.AUTO_REMEDIATING));

  const rows = computed<PanelRow[]>(() => get(issues).map((issue) => {
    const description = describeIssue(issue);
    return {
      description,
      eventRoute: relatedEventRoute(issue.kind, description.eventIdentifier, issue.groupIdentifier, issue.asset),
      issue,
    };
  }));

  async function loadList(append: boolean): Promise<void> {
    const busy = append ? loadingMore : loading;
    set(busy, true);
    try {
      const collection = await fetchData(buildPanelPayload(toValue(filters), get(offset)));
      set(issues, append ? [...get(issues), ...collection.data] : collection.data);
      set(total, collection.found);
    }
    finally {
      set(busy, false);
    }
  }

  /** Reloads from the first page, replacing the current list (on mount, filter change, refresh). */
  async function refreshList(): Promise<void> {
    set(offset, 0);
    await loadList(false);
  }

  /** Appends the next page; guarded so overlapping scroll events do not double-fetch. */
  async function loadMore(): Promise<void> {
    if (get(loading) || get(loadingMore) || !get(canLoadMore))
      return;
    set(offset, get(offset) + PANEL_PAGE_SIZE);
    await loadList(true);
  }

  async function reloadAll(): Promise<void> {
    await Promise.all([refreshList(), refreshSummary()]);
  }

  return {
    hasRemediatingRows,
    isEmpty,
    loading: readonly(loading),
    loadingMore: readonly(loadingMore),
    loadMore,
    refreshList,
    reloadAll,
    rows,
  };
}
