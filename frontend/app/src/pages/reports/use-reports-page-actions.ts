import type { DeepReadonly, Ref } from 'vue';
import type { ProfitLossReportDebugPayload, ProfitLossReportPeriod } from '@/modules/reports/report-types';
import { Priority, Severity } from '@rotki/common';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { displayDateFormatter } from '@/modules/core/common/date-formatter';
import { downloadFileByTextContent } from '@/modules/core/common/file/download';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, isCancellation, type TaskError } from '@/modules/core/tasks/task-result';
import { useReportGeneration } from '@/modules/reports/use-report-generation';
import { useReportOperations } from '@/modules/reports/use-report-operations';
import { useReportsApi } from '@/modules/reports/use-reports-api';
import { PinnedNames } from '@/modules/session/types';
import { useSetting } from '@/modules/settings/use-setting';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { usePinnedPanel } from '@/modules/shell/pinned/use-pinned-panel';
import { activityLabel } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

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

  const { submitTask } = useNativeTask();
  const { exportReportData, generateReport } = useReportGeneration();
  const { fetchReports } = useReportOperations();
  const { unpin: unpinReportCard } = usePinnedPanel(PinnedNames.REPORT_ACTIONABLE_CARD);
  const { notify, showErrorMessage, showSuccessMessage } = useNotifications();
  const dateDisplayFormat = useSetting('dateDisplayFormat');
  const { appSession, openDirectory } = useInterop();
  const { importReportData, uploadReportData } = useReportsApi();

  const importDataLoading = shallowRef<boolean>(false);

  async function generate(period: ProfitLossReportPeriod): Promise<void> {
    // Clear the report-issues pin (if it is the active one) before regenerating.
    unpinReportCard();

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

    const outcome = await submitTask<boolean>({
      id: makeActivityId(ActivityKind.PNL_REPORT, ActivityPart.IMPORT),
      kind: ActivityKind.PNL_REPORT,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<boolean, TaskError>> => mapResult(
        await runTask<boolean>(
          async () => path ? importReportData(path) : uploadReportData(file),
        ),
        value => value,
      ),
      subtitle: activityLabel(ActivityKind.PNL_REPORT, ActivityPart.IMPORT),
      title: t('profit_loss_reports.debug.import_message.title'),
    });

    if (!isErr(outcome)) {
      if (outcome.value) {
        showSuccessMessage(t('profit_loss_reports.debug.import_message.title'), t('profit_loss_reports.debug.import_message.success'));
        await fetchReports();
      }
      else {
        showErrorMessage(t('profit_loss_reports.debug.import_message.title'), t('profit_loss_reports.debug.import_message.failure', { message: '' }));
      }
    }
    else if (isCancellation(outcome.error)) {
      await fetchReports();
    }
    else if (isActionable(outcome.error)) {
      showErrorMessage(t('profit_loss_reports.debug.import_message.title'), t('profit_loss_reports.debug.import_message.failure', { message: outcome.error.message }));
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
