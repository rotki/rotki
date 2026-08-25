import type { ComputedRef, DeepReadonly, Ref } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { ProfitLossEvent, Report } from '@/modules/reports/report-types';
import { useReportOperations } from '@/modules/reports/use-report-operations';
import { defaultReportEvents, useReportsStore } from '@/modules/reports/use-reports-store';

/**
 * The query param `reports/index` sets when it sends the user here after generating a report.
 * Consumed once on mount and then cleared, so a reload does not reopen the panel.
 */
const OPEN_REPORT_ACTIONABLE_QUERY = 'openReportActionable';

interface UseReportDetailReturn {
  eventsSkippedCount: ComputedRef<number>;
  hasActionableIssues: ComputedRef<boolean>;
  initialOpenReportActionable: DeepReadonly<Ref<boolean>>;
  latest: ComputedRef<boolean>;
  loading: DeepReadonly<Ref<boolean>>;
  missingAcquisitionsCount: ComputedRef<number>;
  missingPricesCount: ComputedRef<number>;
  modelReportEvents: Ref<Collection<ProfitLossEvent>>;
  refreshing: DeepReadonly<Ref<boolean>>;
  regenerateReport: () => Promise<void>;
  reportId: number;
  selectedReport: ComputedRef<Report>;
  settings: ComputedRef<Report['settings']>;
  showCompletenessWarning: ComputedRef<boolean>;
  showStaleDetails: ComputedRef<boolean>;
}

export function useReportDetail(): UseReportDetailReturn {
  const reportsStore = useReportsStore();
  const { actionableItems, reports } = storeToRefs(reportsStore);
  const { isLatestReport } = reportsStore;
  const { fetchReports, getActionableItems } = useReportOperations();

  const router = useRouter();
  const route = useRoute<'/reports/[id]'>();
  const reportId = Number(String(get(route).params.id));
  const latest = isLatestReport(reportId);

  const loading = shallowRef<boolean>(true);
  const refreshing = shallowRef<boolean>(false);
  const initialOpenReportActionable = shallowRef<boolean>(false);
  const modelReportEvents = ref<Collection<ProfitLossEvent>>(defaultReportEvents());

  function findReport(): Report | undefined {
    return get(reports).entries.find(item => item.identifier === reportId);
  }

  const selectedReport = computed<Report>(() => findReport()!);
  const settings = computed<Report['settings']>(() => get(selectedReport).settings);

  const missingAcquisitionsCount = computed<number>(() => get(actionableItems)?.missingAcquisitions.length ?? 0);
  const missingPricesCount = computed<number>(() => get(actionableItems)?.missingPrices.length ?? 0);
  const eventsSkippedCount = computed<number>(() => get(actionableItems)?.eventsSkippedNoRule ?? 0);
  const hasActionableIssues = computed<boolean>(() => get(latest) && (get(missingAcquisitionsCount) > 0 || get(missingPricesCount) > 0));
  const showCompletenessWarning = computed<boolean>(() => get(hasActionableIssues) || (get(latest) && get(eventsSkippedCount) > 0));

  // Detailed issues are only kept for the latest report. For older reports we can still tell
  // whether they had incomplete processing, and only then is it worth explaining why the details
  // are unavailable.
  const reportHadIssues = computed<boolean>(() => {
    const report = findReport();
    return !!report && report.processedActions < report.totalActions;
  });
  const showStaleDetails = computed<boolean>(() => !get(latest) && get(reportHadIssues));

  onMounted(async () => {
    set(loading, true);
    if (get(reports).entries.length === 0)
      await fetchReports();

    if (get(latest))
      await getActionableItems();

    if (get(route).query[OPEN_REPORT_ACTIONABLE_QUERY]) {
      set(initialOpenReportActionable, true);
      await router.replace({ query: {} });
    }

    set(loading, false);
  });

  async function regenerateReport(): Promise<void> {
    const { endTs, startTs } = get(selectedReport);
    await router.push({
      path: '/reports',
      query: {
        end: endTs.toString(),
        regenerate: 'true',
        start: startTs.toString(),
      },
    });
  }

  return {
    eventsSkippedCount,
    hasActionableIssues,
    initialOpenReportActionable: readonly(initialOpenReportActionable),
    latest,
    loading: readonly(loading),
    missingAcquisitionsCount,
    missingPricesCount,
    modelReportEvents,
    refreshing: readonly(refreshing),
    regenerateReport,
    reportId,
    selectedReport,
    settings,
    showCompletenessWarning,
    showStaleDetails,
  };
}
