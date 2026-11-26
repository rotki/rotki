import type { DeepReadonly, Ref } from 'vue';
import type { ProfitLossReportDebugPayload, ProfitLossReportPeriod } from '@/modules/reports/report-types';
import { NotificationKind, Severity } from '@rotki/common';
import { get } from '@vueuse/shared';
import { useI18n } from 'vue-i18n';
import { displayDateFormatter } from '@/modules/core/common/date-formatter';
import { downloadFileByTextContent } from '@/modules/core/common/file/download';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { useReportDebugImport } from '@/modules/reports/use-report-debug-import';
import { useReportGeneration } from '@/modules/reports/use-report-generation';
import { PinnedNames } from '@/modules/session/types';
import { useSetting } from '@/modules/settings/use-setting';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { usePinnedPanel } from '@/modules/shell/pinned/use-pinned-panel';

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

  const { exportReportData, generateReport } = useReportGeneration();
  const { unpin: unpinReportCard } = usePinnedPanel(PinnedNames.REPORT_ACTIONABLE_CARD);
  const { notify, notifyError } = useNotifications();
  const dateDisplayFormat = useSetting('dateDisplayFormat');
  const { appSession, openDirectory } = useInterop();
  const { importData, importDataLoading } = useReportDebugImport({ getPath, reportDebugData });

  /**
   * Generates a report for the period and navigates to it.
   *
   * @remarks
   * The report-issues pin is cleared first, when it is the active one. It describes the report
   * being replaced, so leaving it up would show issues against a report that no longer exists.
   */
  async function generate(period: ProfitLossReportPeriod): Promise<void> {
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
        message: t('profit_loss_reports.notification.message', {
          end: formatDate(period.end),
          start: formatDate(period.start),
        }),
        kind: NotificationKind.RESULT,
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
      if (result === null)
        return;

      if (!appSession)
        downloadFileByTextContent(JSON.stringify(result, null, 2), 'pnl_debug.json', 'application/json');
    }
    catch (error: unknown) {
      notifyError(t('profit_loss_reports.debug.export_message.title'), getErrorMessage(error));
    }
  }

  return {
    exportData,
    generate,
    importData,
    importDataLoading,
  };
}
