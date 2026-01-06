import type { Ref } from 'vue';
import type { ProfitLossReportDebugPayload, ProfitLossReportPeriod } from '@/types/reports';
import type { TaskMeta } from '@/types/task';
import { Priority, Severity } from '@rotki/common';
import { useReportsApi } from '@/composables/api/reports';
import { useInterop } from '@/composables/electron-interop';
import { displayDateFormatter } from '@/data/date-formatter';
import { useMessageStore } from '@/store/message';
import { useNotificationsStore } from '@/store/notifications';
import { useReportsStore } from '@/store/reports';
import { useAreaVisibilityStore } from '@/store/session/visibility';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { downloadFileByTextContent } from '@/utils/download';

interface UseReportsPageActionsOptions {
  getPath: (file: File) => string | undefined;
  onNavigateToReport: (reportId: number) => void;
  reportDebugData: Ref<File | undefined>;
}

interface UseReportsPageActionsReturn {
  exportData: (period: ProfitLossReportPeriod) => Promise<void>;
  generate: (period: ProfitLossReportPeriod) => Promise<void>;
  importData: () => Promise<void>;
  importDataLoading: Ref<boolean>;
}

export function useReportsPageActions(options: UseReportsPageActionsOptions): UseReportsPageActionsReturn {
  const { getPath, onNavigateToReport, reportDebugData } = options;

  const { t } = useI18n({ useScope: 'global' });

  const { awaitTask } = useTaskStore();
  const reportsStore = useReportsStore();
  const { exportReportData, fetchReports, generateReport } = reportsStore;
  const { pinned } = storeToRefs(useAreaVisibilityStore());
  const { notify } = useNotificationsStore();
  const { dateDisplayFormat } = storeToRefs(useGeneralSettingsStore());
  const { setMessage } = useMessageStore();
  const { appSession, openDirectory } = useInterop();
  const { importReportData, uploadReportData } = useReportsApi();

  const importDataLoading = ref<boolean>(false);

  async function generate(period: ProfitLossReportPeriod): Promise<void> {
    if (get(pinned)?.name === 'report-actionable-card')
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
        setMessage({
          description: result
            ? t('profit_loss_reports.debug.export_message.success')
            : t('profit_loss_reports.debug.export_message.failure'),
          success: !!result,
          title: t('profit_loss_reports.debug.export_message.title'),
        });
      }
      else {
        downloadFileByTextContent(JSON.stringify(result, null, 2), 'pnl_debug.json', 'application/json');
      }
    }
    catch (error: any) {
      setMessage({
        description: error.message,
        success: false,
        title: t('profit_loss_reports.debug.export_message.title'),
      });
    }
  }

  async function importData(): Promise<void> {
    if (!isDefined(reportDebugData))
      return;

    set(importDataLoading, true);

    let success: boolean;
    let message = '';

    const taskType = TaskType.IMPORT_PNL_REPORT_DATA;
    const file = get(reportDebugData);

    try {
      const path = getPath(file);
      const { taskId } = path
        ? await importReportData(path)
        : await uploadReportData(file);

      const { result } = await awaitTask<boolean, TaskMeta>(taskId, taskType, {
        title: t('profit_loss_reports.debug.import_message.title'),
      });
      success = result;
    }
    catch (error: any) {
      if (isTaskCancelled(error)) {
        await fetchReports();
        set(importDataLoading, false);
        return;
      }

      message = error.message;
      success = false;
    }

    if (!success) {
      setMessage({
        description: t('profit_loss_reports.debug.import_message.failure', {
          message,
        }),
        title: t('profit_loss_reports.debug.import_message.title'),
      });
    }
    else {
      setMessage({
        description: t('profit_loss_reports.debug.import_message.success'),
        success: true,
        title: t('profit_loss_reports.debug.import_message.title'),
      });
      await fetchReports();
    }

    set(importDataLoading, false);
  }

  return {
    exportData,
    generate,
    importData,
    importDataLoading,
  };
}
