import type { ProfitLossReportDebugPayload, ProfitLossReportPeriod } from '@/modules/reports/report-types';
import { getOr, isErr, isOk, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { convertFromTimestamp } from '@/modules/core/common/data/date';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { useHistoryApi } from '@/modules/history/api/use-history-api';
import { useReportOperations } from '@/modules/reports/use-report-operations';
import { useReportsApi } from '@/modules/reports/use-reports-api';
import { useReportsStore } from '@/modules/reports/use-reports-store';
import { activityLabel, activityLabelFor } from '@/modules/task-center/activity-labels';
import { type ActivityId, ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseReportGenerationReturn {
  exportReportData: (payload: ProfitLossReportDebugPayload) => Promise<boolean | object>;
  generateReport: (period: ProfitLossReportPeriod) => Promise<number>;
}

/**
 * Generates / exports a P&L report as native PNL_REPORT orchestrator activities. The orchestrator
 * owns liveness, cancellation and (for generation) re-run; the report page keeps its own richer
 * progress store (the textual `processingState`), and the polled percentage is also pushed onto
 * the activity so the task center shows a matching bar.
 */
export function useReportGeneration(): UseReportGenerationReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { lastGeneratedReport, reportError, reportProgress } = storeToRefs(useReportsStore());

  const { fetchReports } = useReportOperations();
  const { reportProgress: pushProgress, submitTask } = useNativeTask();
  const { getProgress } = useHistoryApi();
  const { exportReportData: exportReportDataCaller, generateReport: generateReportCaller } = useReportsApi();

  function emptyError(): { error: string; message: string } {
    return { error: '', message: '' };
  }

  function resetProgress(): void {
    set(reportProgress, { processingState: '', totalProgress: '0' });
  }

  let activeInterval: NodeJS.Timeout | undefined;

  /** Poll backend report status into the store and mirror the percentage onto the activity. */
  function checkProgress(activityId: ActivityId): NodeJS.Timeout {
    const interval = setInterval(() => {
      getProgress()
        .then((progress) => {
          set(reportProgress, progress);
          const current = Number.parseInt(progress.totalProgress);
          if (Number.isFinite(current))
            pushProgress(activityId, { current, total: 100 });
        })
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

    const id = makeActivityId(ActivityKind.PNL_REPORT);
    const intervalId = checkProgress(id);
    const outcome = await submitTask<number>({
      cleanup: () => {
        clearInterval(intervalId);
        resetProgress();
      },
      id,
      kind: ActivityKind.PNL_REPORT,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<number, TaskError>> => {
        const result = await runTask<number>(
          async () => generateReportCaller(period),
        );
        if (isErr(result))
          return result;

        // A re-run regenerates with the same period, so the success side effects live in `run`.
        if (result.value) {
          set(lastGeneratedReport, result.value);
          await fetchReports();
        }
        return result;
      },
      subtitle: activityLabelFor(msg.$t('task_center.activity.pnl_report.generate'), { period: `${convertFromTimestamp(period.start)} - ${convertFromTimestamp(period.end)}` }),
      title: t('task_center.group.pnl_report'),
    });

    // A backend success with an empty report id is a soft error the page surfaces.
    if (isOk(outcome) && !outcome.value) {
      set(reportError, {
        error: '',
        message: t('actions.reports.generate.error.description', { error: '' }),
      });
    }

    onActionableError(outcome, (error) => {
      set(reportError, {
        error: error.message,
        message: t('actions.reports.generate.error.description'),
      });
    });

    return getOr(outcome, -1);
  }

  async function exportReportData(payload: ProfitLossReportDebugPayload): Promise<boolean | object> {
    resetProgress();
    set(reportError, emptyError());

    const id = makeActivityId(ActivityKind.PNL_REPORT, ActivityPart.EXPORT);
    const intervalId = checkProgress(id);
    const outcome = await submitTask<boolean | object>({
      cleanup: () => {
        clearInterval(intervalId);
        resetProgress();
      },
      id,
      kind: ActivityKind.PNL_REPORT,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<boolean | object, TaskError>> => runTask<boolean | object>(
        async () => exportReportDataCaller(payload),
      ),
      subtitle: activityLabel(ActivityKind.PNL_REPORT, ActivityPart.EXPORT),
      title: t('task_center.group.pnl_report'),
    });

    onActionableError(outcome, (error) => {
      set(reportError, {
        error: error.message,
        message: t('actions.reports.generate.error.description'),
      });
    });

    return getOr(outcome, {});
  }

  return {
    exportReportData,
    generateReport,
  };
}
