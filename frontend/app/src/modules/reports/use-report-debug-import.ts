import { set } from '@vueuse/shared';
import { isErr, type Result } from 'plainfp/result';
import { type DeepReadonly, type MaybeRefOrGetter, readonly, type Ref, shallowRef, toValue } from 'vue';
import { useI18n } from 'vue-i18n';
import { isCancellation, type TaskError } from '@/modules/core/tasks/task-result';
import { pnlReportImportActivity } from '@/modules/reports/reports.activity';
import { useReportOperations } from '@/modules/reports/use-report-operations';
import { useReportsApi } from '@/modules/reports/use-reports-api';
import { activityLabel } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseReportDebugImportOptions {
  /** Resolves a local file path from a File object (Electron only) */
  getPath: (file: File) => string | undefined;
  /** The selected debug data file for import */
  reportDebugData: MaybeRefOrGetter<File | undefined>;
}

interface UseReportDebugImportReturn {
  importData: () => Promise<void>;
  importDataLoading: DeepReadonly<Ref<boolean>>;
}

/**
 * Imports a PnL debug data file as a task, by path where the app can resolve one and by upload
 * otherwise, then refreshes the report list.
 */
export function useReportDebugImport(options: UseReportDebugImportOptions): UseReportDebugImportReturn {
  const { getPath, reportDebugData } = options;

  const { t } = useI18n({ useScope: 'global' });

  const { submitTask } = useNativeTask();
  const { fetchReports } = useReportOperations();
  const { importReportData, uploadReportData } = useReportsApi();

  const importDataLoading = shallowRef<boolean>(false);

  async function importData(): Promise<void> {
    const file = toValue(reportDebugData);
    if (!file)
      return;

    set(importDataLoading, true);

    const path = getPath(file);

    const outcome = await submitTask<boolean>({
      id: pnlReportImportActivity.id(),
      kind: pnlReportImportActivity.kind,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<boolean, TaskError>> => runTask<boolean>(
        async () => path ? importReportData(path) : uploadReportData(file),
      ),
      subtitle: activityLabel(ActivityKind.PNL_REPORT, ActivityPart.IMPORT),
      title: t('profit_loss_reports.debug.import_message.title'),
    });

    if (!isErr(outcome) || isCancellation(outcome.error))
      await fetchReports();

    set(importDataLoading, false);
  }

  return {
    importData,
    importDataLoading: readonly(importDataLoading),
  };
}
