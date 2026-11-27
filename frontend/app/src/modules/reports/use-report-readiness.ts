import type { DataIssue } from '@/modules/history/data-issues/schemas';
import type { ReportReadiness } from '@/modules/reports/readiness-types';
import { startPromise } from '@shared/utils';
import { get, set } from '@vueuse/shared';
import { computed, type ComputedRef, type MaybeRefOrGetter, onMounted, readonly, ref, type Ref, shallowReadonly, shallowRef, toValue, watch } from 'vue';
import { watchDebounced } from '@/modules/core/common/async/scoped-timers';
import { isAccountingUpdateEnabled } from '@/modules/core/common/feature-flags';
import { useDataIssuesApi } from '@/modules/history/data-issues/api/use-data-issues-api';
import { IssueKind, NON_TERMINAL_STATES } from '@/modules/history/data-issues/constants';
import { sortIssuesByImpact } from '@/modules/history/data-issues/pnl-transforms';
import { useDataIssuesAutoReload } from '@/modules/history/data-issues/use-data-issues-auto-reload';
import { useReportsApi } from '@/modules/reports/use-reports-api';

const CHECKLIST_ISSUE_LIMIT = 100;

/** Display order for grouped issues in the checklist: PnL blockers first, then balance issues. */
const KIND_DISPLAY_ORDER: readonly IssueKind[] = [
  IssueKind.MISSING_PRICE,
  IssueKind.MISSING_COST_BASIS,
  IssueKind.INCOMPLETE_SWAP,
  IssueKind.UNMATCHED_EXCHANGE_TRANSFER,
  IssueKind.NEGATIVE_BALANCE,
  IssueKind.INVALID_EVENT_AMOUNT,
  IssueKind.CURRENT_BALANCE_MISMATCH,
  IssueKind.REBASING_TOKEN,
  IssueKind.UNMATCHED_BRIDGE,
] as const;

export interface IssueGroup {
  readonly kind: IssueKind;
  readonly issues: DataIssue[];
  readonly totalCount: number;
}

interface UseReportReadinessOptions {
  /** Optional lower period bound in unix seconds. */
  readonly startTs?: MaybeRefOrGetter<number | undefined>;
  /** Optional upper period bound in unix seconds; open issues through this bound block readiness. */
  readonly endTs?: MaybeRefOrGetter<number | undefined>;
}

interface UseReportReadinessReturn {
  readonly enabled: boolean;
  readonly error: Readonly<Ref<unknown>>;
  readonly groupedIssues: ComputedRef<IssueGroup[]>;
  readonly issuesError: Readonly<Ref<unknown>>;
  readonly issuesLoading: Readonly<Ref<boolean>>;
  readonly loading: Readonly<Ref<boolean>>;
  readonly modelExpanded: Ref<boolean>;
  readonly readiness: Readonly<Ref<ReportReadiness | undefined>>;
  readonly refresh: () => Promise<void>;
}

/**
 * Fetches PnL report readiness for `[startTs, endTs]` and lazily loads open issues (`<= endTs`)
 * grouped by `IssueKind` and sorted by impact/timestamp when the checklist is expanded.
 */
export function useReportReadiness(options: UseReportReadinessOptions): UseReportReadinessReturn {
  const enabled = isAccountingUpdateEnabled();
  const { fetchReportReadiness } = useReportsApi();
  const { listIssues } = useDataIssuesApi();

  const readiness = ref<ReportReadiness>();
  const issues = ref<DataIssue[]>([]);
  const loading = shallowRef<boolean>(false);
  const issuesLoading = shallowRef<boolean>(false);
  const error = shallowRef<unknown>();
  const issuesError = shallowRef<unknown>();
  const modelExpanded = shallowRef<boolean>(false);

  const groupedIssues = computed<IssueGroup[]>(() => {
    const byKind = new Map<IssueKind, DataIssue[]>();
    for (const issue of get(issues)) {
      const existing = byKind.get(issue.kind);
      if (existing)
        existing.push(issue);
      else
        byKind.set(issue.kind, [issue]);
    }

    const counts = get(readiness)?.openIssuesByKind ?? {};
    const groups: IssueGroup[] = [];
    for (const kind of KIND_DISPLAY_ORDER) {
      const list = byKind.get(kind);
      if (list && list.length > 0) {
        groups.push({
          issues: sortIssuesByImpact(list),
          kind,
          totalCount: counts[kind] ?? list.length,
        });
      }
    }
    return groups;
  });

  async function loadIssues(): Promise<void> {
    if (!enabled)
      return;

    set(issuesLoading, true);
    set(issuesError, undefined);
    const endTs = toValue(options.endTs);
    const toTimestamp = get(readiness)?.evaluatedThroughTs
      ?? (endTs !== undefined && endTs > 0 ? endTs * 1000 : undefined);
    const result = await listIssues({
      limit: CHECKLIST_ISSUE_LIMIT,
      offset: 0,
      state: [...NON_TERMINAL_STATES],
      ...(toTimestamp !== undefined ? { toTimestamp } : {}),
    });
    set(issuesLoading, false);

    if (result.ok) {
      set(issues, result.value.data);
    }
    else {
      set(issuesError, result.error);
    }
  }

  async function loadReadiness(): Promise<void> {
    if (!enabled)
      return;

    set(loading, true);
    set(error, undefined);
    try {
      const result = await fetchReportReadiness({
        fromTimestamp: toValue(options.startTs),
        toTimestamp: toValue(options.endTs),
      });
      set(readiness, result);
      if (result.openIssuesCount === 0)
        set(issues, []);
    }
    catch (error_: unknown) {
      set(error, error_);
    }
    finally {
      set(loading, false);
    }
  }

  async function refresh(): Promise<void> {
    if (!enabled)
      return;

    await loadReadiness();
    if (get(modelExpanded) && (get(readiness)?.openIssuesCount ?? 0) > 0)
      await loadIssues();
  }

  watch(modelExpanded, (expanded) => {
    if (expanded && (get(readiness)?.openIssuesCount ?? 0) > 0)
      startPromise(loadIssues());
  });

  watchDebounced(
    [(): number | undefined => toValue(options.startTs), (): number | undefined => toValue(options.endTs)],
    () => {
      startPromise(refresh());
    },
    { debounce: 200 },
  );

  useDataIssuesAutoReload(refresh);

  onMounted(() => {
    startPromise(refresh());
  });

  return {
    enabled,
    error: shallowReadonly(error),
    groupedIssues,
    issuesError: shallowReadonly(issuesError),
    issuesLoading: readonly(issuesLoading),
    loading: readonly(loading),
    modelExpanded,
    readiness: shallowReadonly(readiness),
    refresh,
  };
}
