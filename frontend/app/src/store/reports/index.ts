import { Blockchain, type Message } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { CURRENCY_USD } from '@/types/currencies';
import { TaskType } from '@/types/task-type';
import { isBlockchain } from '@/types/blockchain/chains';
import { jsonTransformer } from '@/services/axios-transformers';
import { getEthAddressesFromText } from '@/utils/history';
import { isTaskCancelled } from '@/utils';
import { isTransactionEvent } from '@/utils/report';
import { logger } from '@/utils/logging';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useTaskStore } from '@/store/tasks';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useMessageStore } from '@/store/message';
import { useNotificationsStore } from '@/store/notifications';
import { useReportsApi } from '@/composables/api/reports';
import { useHistoryApi } from '@/composables/api/history';
import type {
  ProfitLossReportDebugPayload,
  ProfitLossReportPeriod,
  ReportActionableItem,
  ReportError,
  Reports,
  SelectedReport,
} from '@/types/reports';
import type { TaskMeta } from '@/types/task';
import type { AddressBookSimplePayload } from '@/types/eth-names';

function notify(info: { title: string; message: (value: { message: string }) => string; error?: any }): void {
  logger.error(info.error);
  const message = info.error?.message ?? info.error ?? '';
  const { notify } = useNotificationsStore();
  notify({
    display: true,
    message: info.message({ message }),
    title: info.title,
  });
}

function emptyError(): ReportError {
  return {
    error: '',
    message: '',
  };
}

function defaultReport(): SelectedReport {
  return {
    end: 0,
    entries: [],
    entriesFound: 0,
    entriesLimit: 0,
    firstProcessedTimestamp: 0,
    lastProcessedTimestamp: 0,
    overview: {},
    processedActions: 0,
    settings: {
      calculatePastCostBasis: false,
      includeCrypto2crypto: false,
      includeFeesInCostBasis: true,
      includeGasCosts: false,
      profitCurrency: CURRENCY_USD,
      taxfreeAfterPeriod: 0,
    },
    start: 0,
    totalActions: 0,
  };
}

function defaultReports(): Reports {
  return {
    entries: [],
    entriesFound: 0,
    entriesLimit: 0,
  };
}

interface Progress {
  processingState: string;
  totalProgress: string;
}

function defaultProgress(): Progress {
  return {
    processingState: '',
    totalProgress: '',
  };
}

export const useReportsStore = defineStore('reports', () => {
  const report = ref<SelectedReport>(defaultReport());
  const reports = ref<Reports>(defaultReports());
  const loaded = ref(false);
  const reportProgress = ref<Progress>(defaultProgress());
  const reportError = ref(emptyError());
  const lastGeneratedReport = ref<number | null>(null);
  const actionableItems = ref<ReportActionableItem>({
    missingAcquisitions: [],
    missingPrices: [],
  });

  const { setMessage } = useMessageStore();
  const { t } = useI18n();
  const { itemsPerPage } = storeToRefs(useFrontendSettingsStore());

  const { fetchEnsNames } = useAddressesNamesStore();

  const {
    deleteReport: deleteReportCaller,
    exportReportCSV,
    exportReportData: exportReportDataCaller,
    fetchActionableItems,
    fetchReportEvents,
    fetchReports: fetchReportsCaller,
    generateReport: generateReportCaller,
  } = useReportsApi();

  const { getProgress } = useHistoryApi();

  const isLatestReport = (reportId: number): ComputedRef<boolean> => computed<boolean>(() => get(lastGeneratedReport) === reportId);

  const checkProgress = (): NodeJS.Timeout => {
    const interval = setInterval(() => {
      getProgress()
        .then(progress => set(reportProgress, progress))
        .catch(() => {
          // if the request fails (e.g. user logged out) it stops the interval
          clearInterval(interval);
        });
    }, 2000);
    return interval;
  };

  const createCsv = async (path: string): Promise<void> => {
    let message: Message;
    try {
      const success = await exportReportCSV(path);
      message = {
        description: success
          ? t('actions.reports.csv_export.message.success')
          : t('actions.reports.csv_export.message.failure'),
        success,
        title: t('actions.reports.csv_export.title'),
      };
    }
    catch (error: any) {
      message = {
        description: error.message,
        success: false,
        title: t('actions.reports.csv_export.title'),
      };
    }
    setMessage(message);
  };

  const fetchReports = async (): Promise<void> => {
    try {
      set(reports, await fetchReportsCaller());
    }
    catch (error: any) {
      notify({
        error,
        message: value => t('actions.reports.fetch.error.description', value),
        title: t('actions.reports.fetch.error.title'),
      });
    }
  };

  const deleteReport = async (reportId: number): Promise<void> => {
    try {
      await deleteReportCaller(reportId);
      await fetchReports();
    }
    catch (error: any) {
      notify({
        error,
        message: values => t('actions.reports.delete.error.description', values),
        title: t('actions.reports.delete.error.title'),
      });
    }
  };

  const fetchReport = async (reportId: number, page?: { limit: number; offset: number }): Promise<boolean> => {
    set(loaded, false);
    const currentPage = page ?? { limit: get(itemsPerPage), offset: 0 };

    try {
      const selectedReport = get(reports).entries.find(value => value.identifier === reportId);

      if (!selectedReport)
        return false;

      const reportEntries = await fetchReportEvents(reportId, currentPage);
      set(report, {
        ...reportEntries,
        end: selectedReport.endTs,
        firstProcessedTimestamp: selectedReport.firstProcessedTimestamp,
        lastProcessedTimestamp: selectedReport.lastProcessedTimestamp,
        overview: selectedReport.overview,
        processedActions: selectedReport.processedActions,
        settings: selectedReport.settings,
        start: selectedReport.startTs,
        totalActions: selectedReport.totalActions,
      });

      if (isLatestReport(reportId)) {
        const actionable = await fetchActionableItems();
        set(actionableItems, actionable);
      }
      set(loaded, false);

      const addressesNamesPayload: AddressBookSimplePayload[] = [];
      reportEntries.entries
        .filter(event => isTransactionEvent(event))
        .forEach((event) => {
          const blockchain = event.location || Blockchain.ETH;
          if (!event.notes || !isBlockchain(blockchain))
            return;

          const addresses = getEthAddressesFromText(event.notes);
          addressesNamesPayload.push(
            ...addresses.map(address => ({
              address,
              blockchain,
            })),
          );
        });

      if (addressesNamesPayload.length > 0)
        startPromise(fetchEnsNames(addressesNamesPayload));
    }
    catch (error: any) {
      notify({
        error,
        message: value => t('actions.reports.fetch.error.description', value),
        title: t('actions.reports.fetch.error.title'),
      });
      return false;
    }
    return true;
  };

  const generateReport = async (period: ProfitLossReportPeriod): Promise<number> => {
    set(reportProgress, {
      processingState: '',
      totalProgress: '0',
    });
    set(reportError, emptyError());

    const intervalId = checkProgress();

    const { awaitTask } = useTaskStore();
    try {
      const { taskId } = await generateReportCaller(period);
      const { result } = await awaitTask<number, TaskMeta>(taskId, TaskType.TRADE_HISTORY, {
        title: t('actions.reports.generate.task.title'),
      });

      if (result) {
        set(lastGeneratedReport, result);
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
      return result;
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        set(reportError, {
          error: error.message,
          message: t('actions.reports.generate.error.description'),
        });
      }
      return -1;
    }
    finally {
      clearInterval(intervalId);

      set(reportProgress, {
        processingState: '',
        totalProgress: '0',
      });
    }
  };

  const exportReportData = async (payload: ProfitLossReportDebugPayload): Promise<boolean | object> => {
    set(reportProgress, {
      processingState: '',
      totalProgress: '0',
    });
    set(reportError, emptyError());

    const intervalId = checkProgress();

    const { awaitTask } = useTaskStore();
    try {
      const { taskId } = await exportReportDataCaller(payload);
      const { result } = await awaitTask<boolean | object, TaskMeta>(taskId, TaskType.TRADE_HISTORY, {
        title: t('actions.reports.generate.task.title'),
        transformer: [jsonTransformer],
      });

      return result;
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        set(reportError, {
          error: error.message,
          message: t('actions.reports.generate.error.description'),
        });
      }

      return {};
    }
    finally {
      clearInterval(intervalId);

      set(reportProgress, {
        processingState: '',
        totalProgress: '0',
      });
    }
  };

  const progress = computed<string>(() => get(reportProgress).totalProgress);
  const processingState = computed<string>(() => get(reportProgress).processingState);

  const clearError = (): void => {
    set(reportError, emptyError());
  };

  const clearReport = (): void => {
    set(report, defaultReport());
  };

  const reset = (): void => {
    set(reports, defaultReports());
    clearError();
    clearReport();
    set(loaded, false);
  };

  return {
    actionableItems,
    clearError,
    clearReport,
    createCsv,
    deleteReport,
    exportReportData,
    fetchReport,
    fetchReports,
    generateReport,
    isLatestReport,
    loaded,
    processingState,
    progress,
    report,
    reportError,
    reports,
    reset,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useReportsStore, import.meta.hot));
