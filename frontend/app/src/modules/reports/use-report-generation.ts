import type { ProfitLossReportDebugPayload, ProfitLossReportPeriod } from '@/modules/reports/report-types';
import type { TaskMeta } from '@/modules/tasks/types';
import { useHistoryApi } from '@/composables/api/history';
import { useReportsApi } from '@/composables/api/reports';
import { useReportOperations } from '@/modules/reports/use-report-operations';
import { TaskType } from '@/modules/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/tasks/use-task-handler';
import { useReportsStore } from '@/store/reports';

interface UseReportGenerationReturn {
  exportReportData: (payload: ProfitLossReportDebugPayload) => Promise<boolean | object>;
  generateReport: (period: ProfitLossReportPeriod) => Promise<number>;
}

export function useReportGeneration(): UseReportGenerationReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { lastGeneratedReport, reportError, reportProgress } = storeToRefs(useReportsStore());

  const { fetchReports } = useReportOperations();
  const { runTask } = useTaskHandler();
  const { getProgress } = useHistoryApi();
  const { exportReportData: exportReportDataCaller, generateReport: generateReportCaller } = useReportsApi();

  function emptyError(): { error: string; message: string } {
    return { error: '', message: '' };
  }

  function resetProgress(): void {
    set(reportProgress, { processingState: '', totalProgress: '0' });
  }

  let activeInterval: NodeJS.Timeout | undefined;

  function checkProgress(): NodeJS.Timeout {
    const interval = setInterval(() => {
      getProgress()
        .then(progress => set(reportProgress, progress))
        .catch(() => {
          clearInterval(interval);
        });
    }, 2000);
    activeInterval = interval;
    return interval;
  }

  onScopeDispose(() => {
    if (activeInterval) {
      clearInterval(activeInterval);
      activeInterval = undefined;
    }
  });

  async function generateReport(period: ProfitLossReportPeriod): Promise<number> {
    resetProgress();
    set(reportError, emptyError());

    const intervalId = checkProgress();

    try {
      const outcome = await runTask<number, TaskMeta>(
        async () => generateReportCaller(period),
        { type: TaskType.TRADE_HISTORY, meta: { title: t('actions.reports.generate.task.title') } },
      );

      if (outcome.success) {
        if (outcome.result) {
          set(lastGeneratedReport, outcome.result);
          await fetchReports();
        }
        else {
          set(reportError, {
            error: '',
            message: t('actions.reports.generate.error.description', {
              error: '',
            }),
          });
        }
        return outcome.result;
      }
      else if (isActionableFailure(outcome)) {
        set(reportError, {
          error: outcome.message,
          message: t('actions.reports.generate.error.description'),
        });
      }
      return -1;
    }
    finally {
      clearInterval(intervalId);
      resetProgress();
    }
  }

  async function exportReportData(payload: ProfitLossReportDebugPayload): Promise<boolean | object> {
    resetProgress();
    set(reportError, emptyError());

    const intervalId = checkProgress();

    try {
      const outcome = await runTask<boolean | object, TaskMeta>(
        async () => exportReportDataCaller(payload),
        { type: TaskType.TRADE_HISTORY, meta: { title: t('actions.reports.generate.task.title') } },
      );

      if (outcome.success) {
        return outcome.result;
      }
      else if (isActionableFailure(outcome)) {
        set(reportError, {
          error: outcome.message,
          message: t('actions.reports.generate.error.description'),
        });
      }

      return {};
    }
    finally {
      clearInterval(intervalId);
      resetProgress();
    }
  }

  return {
    exportReportData,
    generateReport,
  };
}
