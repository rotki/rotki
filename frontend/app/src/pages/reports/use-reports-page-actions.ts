import type { DeepReadonly, Ref } from 'vue';
import type { ProfitLossReportDebugPayload, ProfitLossReportPeriod } from '@/modules/reports/report-types';
import type { TaskMeta } from '@/modules/tasks/types';
import { Priority, Severity } from '@rotki/common';
import { useReportsApi } from '@/composables/api/reports';
import { useInterop } from '@/composables/electron-interop';
import { displayDateFormatter } from '@/modules/common/date-formatter';
import { downloadFileByTextContent } from '@/modules/common/file/download';
import { useAreaVisibilityStore } from '@/modules/common/use-area-visibility-store';
import { getErrorMessage, useNotifications } from '@/modules/notifications/use-notifications';
import { useReportGeneration } from '@/modules/reports/use-report-generation';
import { useReportOperations } from '@/modules/reports/use-report-operations';
import { PinnedNames } from '@/modules/session/types';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import { TaskType } from '@/modules/tasks/task-type';
import { useTaskHandler } from '@/modules/tasks/use-task-handler';

interface UseReportsPageActionsOptions {
  /** Resolves a local file path from a File object (Electron only) */
  getPath: (file: File) => string | undefined;
  /** Callback to navigate to a specific report after generation */
  onNavigateToReport: (reportId: number) => void;
  /** The selected debug data file for import */
  reportDebugData: Ref<File | undefined>;
}

interface UseReportsPageActionsReturn {
  exportData: (period: ProfitLossReportPeriod) => Promise<void>;
  generate: (period: ProfitLossReportPeriod) => Promise<void>;
  importData: () => Promise<void>;
  importDataLoading: DeepReadonly<Ref<boolean>>;
}

export function useReportsPageActions(options: UseReportsPageActionsOptions): UseReportsPageActionsReturn {
  const { getPath, onNavigateToReport, reportDebugData } = options;

  const { t } = useI18n({ useScope: 'global' });

  const { runTask } = useTaskHandler();
  const { exportReportData, generateReport } = useReportGeneration();
  const { fetchReports } = useReportOperations();
  const { pinned } = storeToRefs(useAreaVisibilityStore());
  const { notify, showErrorMessage, showSuccessMessage } = useNotifications();
  const { dateDisplayFormat } = storeToRefs(useGeneralSettingsStore());
  const { appSession, openDirectory } = useInterop();
  const { importReportData, uploadReportData } = useReportsApi();

  const importDataLoading = shallowRef<boolean>(false);

  async function generate(period: ProfitLossReportPeriod): Promise<void> {
    if (get(pinned)?.name === PinnedNames.REPORT_ACTIONABLE_CARD)
      set(pinned, null);

    const formatDate = (timestamp: number): string =>
      displayDateFormatter.format(new Date(timestamp * 1000), get(dateDisplayFormat));

    const reportId = await generateReport(period);

    if (reportId > 0) {
      onNavigateToReport(reportId);
      notify({
        action: {
          action: () => onNavigateToReport(reportId),
          label: t('profit_loss_reports.notification.action'),
        },
        display: true,
        message: t('profit_loss_reports.notification.message', {
          end: formatDate(period.end),
          start: formatDate(period.start),
        }),
        priority: Priority.ACTION,
        severity: Severity.INFO,
        title: t('profit_loss_reports.notification.title'),
      });
    }
  }

  async function exportData({ end, start }: ProfitLossReportPeriod): Promise<void> {
    const payload: ProfitLossReportDebugPayload = {
      fromTimestamp: start,
      toTimestamp: end,
    };

    try {
      if (appSession) {
        const directoryPath = await openDirectory(t('common.select_directory'));
        if (!directoryPath)
          return;

        payload.directoryPath = directoryPath;
      }

      const result = await exportReportData(payload);

      if (appSession) {
        if (result)
          showSuccessMessage(t('profit_loss_reports.debug.export_message.title'), t('profit_loss_reports.debug.export_message.success'));
        else
          showErrorMessage(t('profit_loss_reports.debug.export_message.title'), t('profit_loss_reports.debug.export_message.failure'));
      }
      else {
        downloadFileByTextContent(JSON.stringify(result, null, 2), 'pnl_debug.json', 'application/json');
      }
    }
    catch (error: unknown) {
      showErrorMessage(t('profit_loss_reports.debug.export_message.title'), getErrorMessage(error));
    }
  }

  async function importData(): Promise<void> {
    if (!isDefined(reportDebugData))
      return;

    set(importDataLoading, true);

    const file = get(reportDebugData);
    const path = getPath(file);

    const outcome = await runTask<boolean, TaskMeta>(
      async () => path ? importReportData(path) : uploadReportData(file),
      { type: TaskType.IMPORT_PNL_REPORT_DATA, meta: { title: t('profit_loss_reports.debug.import_message.title') } },
    );

    if (outcome.success) {
      if (outcome.result) {
        showSuccessMessage(t('profit_loss_reports.debug.import_message.title'), t('profit_loss_reports.debug.import_message.success'));
        await fetchReports();
      }
      else {
        showErrorMessage(t('profit_loss_reports.debug.import_message.title'), t('profit_loss_reports.debug.import_message.failure', { message: '' }));
      }
    }
    else if (outcome.cancelled) {
      await fetchReports();
    }
    else if (!outcome.skipped) {
      showErrorMessage(t('profit_loss_reports.debug.import_message.title'), t('profit_loss_reports.debug.import_message.failure', { message: outcome.message }));
    }

    set(importDataLoading, false);
  }

  return {
    exportData,
    generate,
    importData,
    importDataLoading: readonly(importDataLoading),
  };
}
