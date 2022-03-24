import { Message } from '@rotki/common/lib/messages';
import { computed, Ref, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { acceptHMRUpdate, defineStore } from 'pinia';
import { setupSettings } from '@/composables/settings';
import { CURRENCY_USD } from '@/data/currencies';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { useEnsNamesStore } from '@/store/balances';
import { filterAddressesFromWords } from '@/store/history/utils';
import { useNotifications } from '@/store/notifications';
import { useMainStore } from '@/store/store';
import { useTasks } from '@/store/tasks';
import {
  ProfitLossEvents,
  ProfitLossEventTypeEnum,
  ProfitLossReportPeriod,
  ReportActionableItem,
  ReportError,
  Reports,
  SelectedReport
} from '@/types/reports';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { AccountingSettings } from '@/types/user';
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

const defaultReport = (): SelectedReport => ({
  entries: [] as ProfitLossEvents,
  entriesLimit: 0,
  entriesFound: 0,
  start: 0,
  end: 0,
  firstProcessedTimestamp: 0,
  lastProcessedTimestamp: 0,
  processedActions: 0,
  totalActions: 0,
  overview: {},
  settings: {
    taxfreeAfterPeriod: 0,
    calculatePastCostBasis: false,
    accountForAssetsMovements: false,
    includeGasCosts: false,
    includeCrypto2crypto: false,
    profitCurrency: CURRENCY_USD
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
  const lastGeneratedReport = ref<number | null>(null);
  const actionableItems = ref<ReportActionableItem>({
    missingAcquisitions: [],
    missingPrices: []
  });

  const { setMessage } = useMainStore();

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
    setMessage(message);
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
    set(loaded, false);
    const { itemsPerPage } = setupSettings();
    const currentPage = page ?? { limit: get(itemsPerPage), offset: 0 };

    try {
      const selectedReport = get(reports).entries.find(
        value => value.identifier === reportId
      );

      if (!selectedReport) {
        return false;
      }
      const reportEntries = await api.reports.fetchReportEvents(
        reportId,
        currentPage
      );
      set(report, {
        ...reportEntries,
        overview: selectedReport.overview,
        settings: selectedReport.settings,
        start: selectedReport.startTs,
        end: selectedReport.endTs,
        firstProcessedTimestamp: selectedReport.firstProcessedTimestamp,
        lastProcessedTimestamp: selectedReport.lastProcessedTimestamp,
        totalActions: selectedReport.totalActions,
        processedActions: selectedReport.processedActions
      });

      if (isLatestReport(reportId)) {
        const actionable = await api.reports.fetchActionableItems();
        set(actionableItems, actionable);
      }
      set(loaded, false);
      const words = reportEntries.entries
        .filter(event => {
          return event.type === ProfitLossEventTypeEnum.TRANSACTION_EVENT;
        })
        .map(event => {
          return event.notes;
        })
        .join(' ')
        .split(' ');

      const addresses = filterAddressesFromWords(words);

      const { fetchEnsNames } = useEnsNamesStore();
      fetchEnsNames(addresses, false);
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
      set(reports, await api.reports.fetchReports());
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
    set(reportProgress, {
      processingState: '',
      totalProgress: '0'
    });
    set(reportError, emptyError());

    const interval = setInterval(async () => {
      set(reportProgress, await api.history.getProgress());
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
        set(lastGeneratedReport, result);
        await fetchReports();
      } else {
        set(reportError, {
          error: '',
          message: i18n
            .t('actions.reports.generate.error.description', { error: '' })
            .toString()
        });
      }
      return result;
    } catch (e: any) {
      set(reportError, {
        error: e.message,
        message: i18n.t('actions.reports.generate.error.description').toString()
      });
      return -1;
    } finally {
      clearInterval(interval);

      set(reportProgress, {
        processingState: '',
        totalProgress: '0'
      });
    }
  };

  const progress = computed(() => get(reportProgress).totalProgress);
  const processingState = computed(() => get(reportProgress).processingState);

  const isLatestReport = (reportId: number) =>
    computed(() => {
      return get(lastGeneratedReport) === reportId;
    });

  const clearError = () => {
    set(reportError, emptyError());
  };

  const clearReport = () => {
    set(report, defaultReport());
  };

  const reset = () => {
    set(report, defaultReport());
    set(reports, defaultReports());
    set(loaded, false);
    set(accountingSettings, null);
    set(reportProgress, defaultProgress());
    set(reportError, emptyError());
  };

  return {
    reports,
    report,
    accountingSettings,
    loaded,
    progress,
    processingState,
    reportError,
    actionableItems,
    createCsv,
    generateReport,
    deleteReport,
    fetchReport,
    fetchReports,
    clearReport,
    clearError,
    isLatestReport,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useReports, import.meta.hot));
}
