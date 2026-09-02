import type { ComputedRef, DeepReadonly, Ref } from 'vue';
import type { ProfitLossReportPeriod } from '@/modules/reports/report-types';
import { startPromise } from '@shared/utils';
import { firstQueryValue } from '@/modules/core/table/route';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';
import { useReportsPageActions } from '@/pages/reports/use-reports-page-actions';

/**
 * The query params `reports/[id]` sets when it sends the user back here to regenerate a report.
 * All three must be present, and they are cleared before the run starts so a reload does not
 * regenerate a second time.
 */
const REGENERATE_QUERY = 'regenerate';

interface UseReportsPageOptions {
  /** Clears the file the debug-data uploader is holding; owned by the page, which owns the ref. */
  onResetUploader: () => void;
}

interface UseReportsPageReturn {
  exportData: (period: ProfitLossReportPeriod) => Promise<void>;
  generate: (period: ProfitLossReportPeriod) => Promise<void>;
  handleImportComplete: () => Promise<void>;
  importDataLoading: DeepReadonly<Ref<boolean>>;
  isRunning: ComputedRef<boolean>;
  modelImportDataDialog: Ref<boolean>;
  modelReportDebugData: Ref<File | undefined>;
  navigateToReport: (reportId: number) => void;
}

export function useReportsPage(options: UseReportsPageOptions): UseReportsPageReturn {
  const { onResetUploader } = options;

  const { useIsActive } = useTaskCenter();
  const { getPath } = useInterop();

  const isRunning = useIsActive(ActivityKind.PNL_REPORT);
  const modelImportDataDialog = shallowRef<boolean>(false);
  const modelReportDebugData = shallowRef<File | undefined>();

  const router = useRouter();
  const route = useRoute();

  function navigateToReport(reportId: number): void {
    // Guard against a late generation landing after the user has already navigated away.
    if (get(route).name !== '/reports/')
      return;

    startPromise(router.push({
      name: '/reports/[id]',
      params: { id: reportId.toString() },
      query: { openReportActionable: 'true' },
    }));
  }

  const { exportData, generate, importData, importDataLoading } = useReportsPageActions({
    getPath,
    onNavigateToReport: navigateToReport,
    reportDebugData: modelReportDebugData,
  });

  onMounted(async () => {
    const query = get(route).query;
    if (!query[REGENERATE_QUERY])
      return;

    const start = firstQueryValue(query.start);
    const end = firstQueryValue(query.end);
    if (!(start && end))
      return;

    const period = {
      end: Number.parseInt(end),
      start: Number.parseInt(start),
    };
    await router.replace({ query: {} });
    await generate(period);
  });

  async function handleImportComplete(): Promise<void> {
    await importData();
    set(modelImportDataDialog, false);
    onResetUploader();
    set(modelReportDebugData, undefined);
  }

  return {
    exportData,
    generate,
    handleImportComplete,
    importDataLoading,
    isRunning,
    modelImportDataDialog,
    modelReportDebugData,
    navigateToReport,
  };
}
