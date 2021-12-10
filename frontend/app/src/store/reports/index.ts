import { computed, Ref, ref } from '@vue/composition-api';
import { defineStore } from 'pinia';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { userNotify } from '@/store/notifications/utils';
import store from '@/store/store';
import { useTasks } from '@/store/tasks';
import { Message } from '@/store/types';
import {
  ProfitLossEvents,
  ProfitLossOverview,
  ProfitLossReportPeriod,
  ReportError,
  Reports,
  SelectedReport
} from '@/types/reports';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { AccountingSettings } from '@/types/user';
import { assert } from '@/utils/assertions';
import { Zero } from '@/utils/bignumbers';
import { logger } from '@/utils/logging';

const notify = async (info: {
  title: string;
  message: (value: { message: string }) => string;
  error?: any;
}) => {
  logger.error(info.error);
  const message = info.error?.message ?? info.error ?? '';
  await userNotify({
    title: info.title,
    message: info.message({ message }),
    display: true
  });
};

const emptyError: () => ReportError = () => ({
  error: '',
  message: ''
});

const pnlOverview = (): ProfitLossOverview => ({
  loanProfit: Zero,
  defiProfitLoss: Zero,
  marginPositionsProfitLoss: Zero,
  settlementLosses: Zero,
  ethereumTransactionGasCosts: Zero,
  ledgerActionsProfitLoss: Zero,
  assetMovementFees: Zero,
  generalTradeProfitLoss: Zero,
  taxableTradeProfitLoss: Zero,
  totalTaxableProfitLoss: Zero,
  totalProfitLoss: Zero
});

const defaultReport = () => ({
  overview: pnlOverview(),
  entries: [] as ProfitLossEvents,
  entriesLimit: 0,
  entriesFound: 0,
  start: 0,
  end: 0,
  firstProcessedTimestamp: 0
});

const defaultReports = () => ({
  entries: [],
  entriesLimit: 0,
  entriesFound: 0
});

const defaultProgress = () => ({ processingState: '', totalProgress: '' });

export const useReports = defineStore('reports', () => {
  const report = ref(defaultReport()) as Ref<SelectedReport>;
  const reports = ref<Reports>(defaultReports()) as Ref<Reports>;
  const accountingSettings = ref<AccountingSettings | null>(null);
  const loaded = ref(false);
  const reportProgress = ref(defaultProgress());
  const reportError = ref(emptyError());

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
      await notify({
        title: i18n.t('actions.reports.delete.error.title').toString(),
        message: values =>
          i18n.t('actions.reports.delete.error.description', values).toString(),
        error: e
      });
    }
  };

  const fetchReport = async (
    reportId: number,
    page?: { limit: number; offset: number }
  ) => {
    loaded.value = false;
    const itemsPerPage = store.state.settings!.itemsPerPage;
    const currentPage = page ?? { limit: itemsPerPage, offset: 0 };

    try {
      const selectedReport = reports.value.entries.find(
        value => value.identifier === reportId
      );

      assert(selectedReport);
      const {
        sizeOnDisk,
        startTs,
        endTs,
        identifier,
        timestamp,
        firstProcessedTimestamp,
        ...overview
      } = selectedReport;

      const reportEntries = await api.reports.fetchReportEvents(
        reportId,
        currentPage
      );
      report.value = {
        overview,
        ...reportEntries,
        start: startTs,
        end: endTs,
        firstProcessedTimestamp
      };
      loaded.value = true;
    } catch (e: any) {
      await notify({
        title: i18n.t('actions.reports.fetch.error.title').toString(),
        message: value =>
          i18n.t('actions.reports.fetch.error.description', value).toString(),
        error: e
      });
    }
  };

  const fetchReports = async () => {
    try {
      reports.value = await api.reports.fetchReports();
    } catch (e: any) {
      await notify({
        title: i18n.t('actions.reports.fetch.error.title').toString(),
        message: value =>
          i18n.t('actions.reports.fetch.error.description', value).toString(),
        error: e
      });
    }
  };

  const generateReport = async (period: ProfitLossReportPeriod) => {
    reportProgress.value = {
      processingState: '',
      totalProgress: '0'
    };
    reportError.value = emptyError();

    const interval = setInterval(async () => {
      reportProgress.value = await api.history.getProgress();
    }, 2000);

    const { awaitTask } = useTasks();
    try {
      const { taskId } = await api.reports.generateReport(period);
      const { result } = await awaitTask<boolean, TaskMeta>(
        taskId,
        TaskType.TRADE_HISTORY,
        {
          title: i18n.t('actions.reports.generate.task.title').toString(),
          numericKeys: []
        }
      );

      if (result) {
        await fetchReports();
      } else {
        reportError.value = {
          error: '',
          message: i18n
            .t('actions.reports.generate.error.description', { error: '' })
            .toString()
        };
      }
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

  const clearReport = () => {
    report.value = defaultReport();
  };

  const reset = () => {
    report.value = defaultReport();
    reports.value = defaultReports();
    loaded.value = false;
    accountingSettings.value = null;
    reportProgress.value = defaultProgress();
    reportError.value = emptyError();
  };

  return {
    reports,
    report,
    accountingSettings,
    loaded,
    progress,
    processingState,
    reportError,
    createCsv,
    generateReport,
    deleteReport,
    fetchReport,
    fetchReports,
    clearReport,
    reset
  };
});
