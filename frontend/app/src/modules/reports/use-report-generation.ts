import type { ProfitLossReportDebugPayload, ProfitLossReportPeriod } from '@/modules/reports/report-types';
import type { ActivityId } from '@/modules/task-center/core/types';
import { getOr, isErr, isOk, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { convertFromTimestamp } from '@/modules/core/common/data/date';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { useHistoryApi } from '@/modules/history/api/use-history-api';
import { pnlReportActivity, pnlReportExportActivity } from '@/modules/reports/reports.activity';
import { useReportOperations } from '@/modules/reports/use-report-operations';
import { useReportsApi } from '@/modules/reports/use-reports-api';
import { useReportsStore } from '@/modules/reports/use-reports-store';
import { activityLabelFor, activityLabelOf } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseReportGenerationReturn {
  /** Resolves `null` when the export failed or was cancelled, which its task row reports. */
  exportReportData: (payload: ProfitLossReportDebugPayload) => Promise<boolean | object | null>;
  generateReport: (period: ProfitLossReportPeriod) => Promise<number>;
}

/**
 * The backend's report percentage, held to 0-100.
 *
 * @remarks
 * The backend can report more than 100 (rotki/rotki#13354: overlapping or cancelled runs leave its
 * progress fields mixed), which the dock showed as "120 of 100".
 *
 * @returns the clamped percentage, or undefined when the value is not a number
 */
export function clampProgress(value: string): number | undefined {
  const progress = Number.parseFloat(value);
  if (!Number.isFinite(progress))
    return undefined;
  return Math.min(100, Math.max(0, progress));
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

  /**
   * Poll backend report status into the store and mirror the percentage onto the activity.
   *
   * @remarks
   * Start it only from the spec's `run`, which its `cleanup` pairs with once per run, so a task centre
   * re-run polls too. A `submitTask` that joins a run already in flight drops its own spec, cleanup
   * included, so a poll started outside `run` is never stopped.
   */
  function checkProgress(activityId: ActivityId): NodeJS.Timeout {
    const interval = setInterval(() => {
      getProgress()
        .then((progress) => {
          const current = clampProgress(progress.totalProgress);
          set(reportProgress, { ...progress, totalProgress: current === undefined ? progress.totalProgress : String(current) });
          if (current !== undefined)
            pushProgress(activityId, { current: Math.floor(current), total: 100 });
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

    const id = pnlReportActivity.id();
    let intervalId: NodeJS.Timeout | undefined;
    const outcome = await submitTask<number>({
      cleanup: () => {
        clearInterval(intervalId);
        resetProgress();
      },
      id,
      kind: pnlReportActivity.kind,
      rerunnable: true,
      userStarted: true,
      run: async ({ runTask }): Promise<Result<number, TaskError>> => {
        intervalId = checkProgress(id);
        const result = await runTask<number>(
          async () => generateReportCaller(period),
          { conflictFails: true },
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

  async function exportReportData(payload: ProfitLossReportDebugPayload): Promise<boolean | object | null> {
    resetProgress();
    set(reportError, emptyError());

    const id = pnlReportExportActivity.id();
    let intervalId: NodeJS.Timeout | undefined;
    const outcome = await submitTask<boolean | object>({
      cleanup: () => {
        clearInterval(intervalId);
        resetProgress();
      },
      id,
      kind: pnlReportExportActivity.kind,
      rerunnable: false,
      userStarted: true,
      run: async ({ runTask }): Promise<Result<boolean | object, TaskError>> => {
        intervalId = checkProgress(id);
        return runTask<boolean | object>(
          async () => exportReportDataCaller(payload),
        );
      },
      subtitle: activityLabelOf(pnlReportExportActivity),
      title: t('task_center.group.pnl_report'),
    });

    return getOr(outcome, null);
  }

  return {
    exportReportData,
    generateReport,
  };
}
