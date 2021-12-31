import { computed, Ref, ref } from '@vue/composition-api';
import { acceptHMRUpdate, defineStore } from 'pinia';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { useNotifications } from '@/store/notifications';
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
import { AccountingSettings, BaseAccountingSettings } from '@/types/user';
import { Zero } from '@/utils/bignumbers';
import { logger } from '@/utils/logging';

const notify = (info: {
  title: string;
  message: (value: { message: string }) => string;
  error?: any;
}) => {
  logger.error(info.error);
  const message = info.error?.message ?? info.error ?? '';
  const { notify } = useNotifications();
  notify({
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

const defaultReport = (): SelectedReport => ({
  overview: pnlOverview(),
  entries: [] as ProfitLossEvents,
  entriesLimit: 0,
  entriesFound: 0,
  start: 0,
  end: 0,
  firstProcessedTimestamp: 0,
  lastProcessedTimestamp: 0,
  processedActions: 0,
  totalActions: 0,
  currency: 'USD',
  settings: {
    taxfreeAfterPeriod: 0,
    calculatePastCostBasis: false,
    accountForAssetsMovements: false,
    includeGasCosts: false,
    includeCrypto2crypto: false
  }
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
  const generatedReport = ref(false);

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
      await fetchReports();
    } catch (e: any) {
      notify({
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
  ): Promise<boolean> => {
    loaded.value = false;
    const itemsPerPage = store.state.settings!.itemsPerPage;
    const currentPage = page ?? { limit: itemsPerPage, offset: 0 };

    try {
      const selectedReport = reports.value.entries.find(
        value => value.identifier === reportId
      );

      if (!selectedReport) {
        return false;
      }
      const reportEntries = await api.reports.fetchReportEvents(
        reportId,
        currentPage
      );
      const overview: ProfitLossOverview = {
        assetMovementFees: selectedReport.assetMovementFees,
        defiProfitLoss: selectedReport.defiProfitLoss,
        generalTradeProfitLoss: selectedReport.generalTradeProfitLoss,
        ethereumTransactionGasCosts: selectedReport.ethereumTransactionGasCosts,
        ledgerActionsProfitLoss: selectedReport.ledgerActionsProfitLoss,
        marginPositionsProfitLoss: selectedReport.marginPositionsProfitLoss,
        settlementLosses: selectedReport.settlementLosses,
        taxableTradeProfitLoss: selectedReport.taxableTradeProfitLoss,
        totalProfitLoss: selectedReport.totalProfitLoss,
        totalTaxableProfitLoss: selectedReport.totalTaxableProfitLoss,
        loanProfit: selectedReport.loanProfit
      };
      const settings: BaseAccountingSettings = {
        includeCrypto2crypto: selectedReport.includeCrypto2crypto,
        accountForAssetsMovements: selectedReport.accountForAssetsMovements,
        calculatePastCostBasis: selectedReport.calculatePastCostBasis,
        includeGasCosts: selectedReport.includeGasCosts,
        taxfreeAfterPeriod: selectedReport.taxfreeAfterPeriod
      };
      report.value = {
        overview,
        settings,
        ...reportEntries,
        start: selectedReport.startTs,
        end: selectedReport.endTs,
        firstProcessedTimestamp: selectedReport.firstProcessedTimestamp,
        lastProcessedTimestamp: selectedReport.lastProcessedTimestamp,
        totalActions: selectedReport.totalActions,
        processedActions: selectedReport.processedActions,
        currency: selectedReport.profitCurrency
      };
      loaded.value = true;
    } catch (e: any) {
      notify({
        title: i18n.t('actions.reports.fetch.error.title').toString(),
        message: value =>
          i18n.t('actions.reports.fetch.error.description', value).toString(),
        error: e
      });
      return false;
    }
    return true;
  };

  const fetchReports = async () => {
    try {
      reports.value = await api.reports.fetchReports();
    } catch (e: any) {
      notify({
        title: i18n.t('actions.reports.fetch.error.title').toString(),
        message: value =>
          i18n.t('actions.reports.fetch.error.description', value).toString(),
        error: e
      });
    }
  };

  const generateReport = async (
    period: ProfitLossReportPeriod
  ): Promise<number> => {
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
      const { result } = await awaitTask<number, TaskMeta>(
        taskId,
        TaskType.TRADE_HISTORY,
        {
          title: i18n.t('actions.reports.generate.task.title').toString(),
          numericKeys: []
        }
      );

      if (result) {
        generatedReport.value = true;
        await fetchReports();
      } else {
        reportError.value = {
          error: '',
          message: i18n
            .t('actions.reports.generate.error.description', { error: '' })
            .toString()
        };
      }
      return result;
    } catch (e: any) {
      reportError.value = {
        error: e.message,
        message: i18n.t('actions.reports.generate.error.description').toString()
      };
      return -1;
    } finally {
      clearInterval(interval);

      reportProgress.value = {
        processingState: '',
        totalProgress: '0'
      };
    }
  };

  const progress = computed(() => reportProgress.value.totalProgress);
  const processingState = computed(() => reportProgress.value.processingState);

  const canExport = (reportId: number) =>
    computed(() => {
      const entries = reports.value.entries;
      if (!generatedReport.value || entries.length === 0) {
        return false;
      }
      const reverse = [...entries].sort((a, b) => b.identifier - a.identifier);
      return reverse[0].identifier === reportId;
    });

  const clearError = () => {
    reportError.value = emptyError();
  };

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
    clearError,
    canExport,
    reset
  };
});

if (module.hot) {
  module.hot.accept(acceptHMRUpdate(useReports, module.hot));
}
