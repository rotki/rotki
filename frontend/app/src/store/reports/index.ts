import { computed, Ref, ref } from '@vue/composition-api';
import { defineStore } from 'pinia';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { userNotify } from '@/store/notifications/utils';
import {
  emptyError,
  emptyPeriod,
  tradeHistoryPlaceholder
} from '@/store/reports/const';
import { ReportData } from '@/store/reports/types';
import store from '@/store/store';
import { Message } from '@/store/types';
import { ProfitLossPeriod } from '@/types/pnl';
import { ReportsPayloadData, TradeHistory } from '@/types/reports';
import { createTask, taskCompletion, TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { AccountingSettings } from '@/types/user';
import { logger } from '@/utils/logging';

export const useReports = defineStore('reports', () => {
  const report: Ref<ReportData> = ref({
    overview: tradeHistoryPlaceholder(),
    events: [],
    limit: -1,
    processed: -1,
    firstProcessedTimestamp: -1
  });

  const reports = ref<ReportsPayloadData>({
    entries: [],
    entriesLimit: 0,
    entriesFound: 0
  });

  const accountingSettings = ref<AccountingSettings | null>(null);
  const reportPeriod = ref(emptyPeriod());
  const loaded = ref(false);
  const reportProgress = ref({ processingState: '', totalProgress: '' });
  const reportError = ref(emptyError());
  const showUpgradeMessage = computed(
    () => report.value.limit > 0 && report.value.limit < report.value.processed
  );

  const createCsv = async (path: string) => {
    let message: Message;
    try {
      const success = await api.exportHistoryCSV(path);
      message = {
        title: i18n.t('actions.reports.csv_export.title').toString(),
        description: success
          ? i18n.t('actions.reports.csv_export.message.success').toString()
          : i18n.t('actions.reports.csv_export.message.failure').toString(),
        success
      };
    } catch (e: any) {
      message = {
        title: i18n.t('actions.reports.csv_export.title').toString(),
        description: e.message,
        success: false
      };
    }
    store.commit('setMessage', message, { root: true });
  };

  const deleteReport = async (reportId: number) => {
    const notify = async (error?: any) => {
      logger.error(error);
      const message = error?.message ?? error ?? '';
      await userNotify({
        title: i18n.t('actions.reports.delete.error.title').toString(),
        message: i18n
          .t('actions.reports.delete.error.description', { message })
          .toString(),
        display: true
      });
    };
    try {
      await api.reports.deleteReport(reportId);
      const remainingReports = reports.value.entries.filter(
        x => x.identifier !== reportId
      );
      reports.value = {
        entries: remainingReports,
        entriesFound: remainingReports.length,
        entriesLimit: reports.value.entriesLimit
      };
    } catch (e: any) {
      await notify(e);
    }
  };

  const fetchReport = async (reportId: number) => {
    const notify = async (error?: any) => {
      logger.error(error);
      const message = error?.message ?? error ?? '';
      await userNotify({
        title: i18n.t('actions.reports.fetch.error.title').toString(),
        message: i18n
          .t('actions.reports.fetch.error.description', { message })
          .toString(),
        display: true
      });
    };
    try {
      const overviewResult = await api.reports.fetchReportOverview(reportId);
      const overview = overviewResult.entries[0];
      const eventsResult = await api.reports.fetchReportEvents(reportId);
      const targetReport = reports.value.entries.filter(
        x => x.identifier === reportId
      )[0];
      const startTs = targetReport.startTs;
      const endTs = targetReport.endTs;
      reportPeriod.value = { start: startTs, end: endTs };
      const firstProcessedTimestamp = eventsResult.entries[0].time;

      report.value = {
        overview: overview,
        events: eventsResult.entries,
        limit: eventsResult.entriesLimit,
        processed: eventsResult.entriesFound,
        firstProcessedTimestamp
      };
    } catch (e: any) {
      await notify(e);
    }
  };

  const fetchReports = async () => {
    const notify = async (error?: any) => {
      logger.error(error);
      const message = error?.message ?? error ?? '';
      await userNotify({
        title: i18n.t('actions.reports.fetch.error.title').toString(),
        message: i18n
          .t('actions.reports.fetch.error.description', { message })
          .toString(),
        display: true
      });
    };
    try {
      reports.value = await api.reports.fetchReports();
    } catch (e: any) {
      await notify(e);
    }
  };

  const generateReport = async (period: ProfitLossPeriod) => {
    reportProgress.value = {
      processingState: '',
      totalProgress: '0'
    };
    reportError.value = emptyError();

    const interval = setInterval(async () => {
      reportProgress.value = await api.history.getProgress();
    }, 2000);

    try {
      const { start, end } = period;
      const { taskId } = await api.processTradeHistoryAsync(start, end);
      reportPeriod.value = period;
      const task = createTask(taskId, TaskType.TRADE_HISTORY, {
        title: i18n.t('actions.reports.generate.task.title').toString(),
        numericKeys: [],
        ignoreResult: false
      });
      store.commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<TradeHistory, TaskMeta>(
        TaskType.TRADE_HISTORY
      );

      if (result) {
        const notify = async (error?: any) => {
          logger.error(error);
          const message = error?.message ?? error ?? '';
          await userNotify({
            title: i18n.t('actions.reports.fetch.error.title').toString(),
            message: i18n
              .t('actions.reports.fetch.error.description', { message })
              .toString(),
            display: true
          });
        };
        try {
          reports.value = await api.reports.fetchReports();
        } catch (e: any) {
          await notify(e);
        }
      }

      if (!result || !result.overview || !result.allEvents) {
        reportError.value = {
          error: '',
          message: i18n
            .t('actions.reports.generate.error.description', { error: '' })
            .toString()
        };
        return;
      }

      const {
        overview,
        allEvents,
        eventsLimit,
        eventsProcessed,
        firstProcessedTimestamp
      } = result;

      report.value = {
        overview: overview,
        events: allEvents,
        limit: eventsLimit,
        processed: eventsProcessed,
        firstProcessedTimestamp
      };
    } catch (e: any) {
      reportError.value = {
        error: e.message,
        message: i18n.t('actions.reports.generate.error.description').toString()
      };
    }

    clearInterval(interval);

    reportProgress.value = {
      processingState: '',
      totalProgress: '0'
    };
  };

  const progress = computed(() => reportProgress.value.totalProgress);
  const processingState = computed(() => reportProgress.value.processingState);
  const processed = computed(() => report.value.processed);
  const limit = computed(() => report.value.limit);

  return {
    reports,
    report,
    accountingSettings,
    reportPeriod,
    loaded,
    progress,
    processingState,
    reportError,
    showUpgradeMessage,
    processed,
    limit,
    createCsv,
    generateReport,
    deleteReport,
    fetchReport,
    fetchReports
  };
});
