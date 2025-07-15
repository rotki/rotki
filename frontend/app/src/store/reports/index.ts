import type { Collection, CollectionResponse } from '@/types/collection';
import type { AddressBookSimplePayload } from '@/types/eth-names';
import type {
  ProfitLossEvent,
  ProfitLossEventsPayload,
  ProfitLossReportDebugPayload,
  ProfitLossReportPeriod,
  ReportActionableItem,
  ReportError,
  Reports,
} from '@/types/reports';
import type { TaskMeta } from '@/types/task';
import { Blockchain, type Message } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useHistoryApi } from '@/composables/api/history';
import { useReportsApi } from '@/composables/api/reports';
import { jsonTransformer } from '@/services/axios-transformers';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useMessageStore } from '@/store/message';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import { isBlockchain } from '@/types/blockchain/chains';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { mapCollectionResponse } from '@/utils/collection';
import { getEthAddressesFromText } from '@/utils/history';
import { logger } from '@/utils/logging';
import { isTransactionEvent } from '@/utils/report';

function emptyError(): ReportError {
  return {
    error: '',
    message: '',
  };
}

function defaultReports(): Reports {
  return {
    entries: [],
    entriesFound: 0,
    entriesLimit: 0,
  };
}

export function defaultReportEvents(): Collection<ProfitLossEvent> {
  return {
    data: [],
    found: 0,
    limit: 0,
    total: 0,
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
  const reports = ref<Reports>(defaultReports());
  const reportProgress = ref<Progress>(defaultProgress());
  const reportError = ref(emptyError());
  const lastGeneratedReport = ref<number | null>(null);
  const actionableItems = ref<ReportActionableItem>({
    missingAcquisitions: [],
    missingPrices: [],
  });

  const { setMessage } = useMessageStore();
  const { notify } = useNotificationsStore();
  const { t } = useI18n({ useScope: 'global' });

  const { fetchEnsNames } = useAddressesNamesStore();

  const {
    deleteReport: deleteReportCaller,
    exportReportCSV,
    exportReportData: exportReportDataCaller,
    fetchActionableItems,
    fetchReportEvents: fetchReportEventsCaller,
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
      logger.error(error);
      notify({
        message: t('actions.reports.fetch.error.description'),
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
      logger.error(error);
      notify({
        message: t('actions.reports.delete.error.description'),
        title: t('actions.reports.delete.error.title'),
      });
    }
  };

  function fetchEnsNamesFromTransactions(events: Collection<ProfitLossEvent>): void {
    const addressesNamesPayload: AddressBookSimplePayload[] = [];
    events.data
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

  const fetchReportEvents = async (payload: MaybeRef<ProfitLossEventsPayload>): Promise<Collection<ProfitLossEvent>> => {
    try {
      const response = await fetchReportEventsCaller(get(payload));
      const events = mapCollectionResponse<ProfitLossEvent, CollectionResponse<ProfitLossEvent>>(response);
      fetchEnsNamesFromTransactions(events);
      return events;
    }
    catch (error: any) {
      logger.error(error);
      notify({
        message: t('actions.report_events.fetch.error.description', { error }),
        title: t('actions.report_events.fetch.error.title'),
      });
      return defaultReportEvents();
    }
  };

  const getActionableItems = async (): Promise<void> => {
    const actionable = await fetchActionableItems();
    set(actionableItems, actionable);
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

  const reset = (): void => {
    set(reports, defaultReports());
    clearError();
  };

  return {
    actionableItems,
    clearError,
    createCsv,
    deleteReport,
    exportReportData,
    fetchReportEvents,
    fetchReports,
    generateReport,
    getActionableItems,
    isLatestReport,
    processingState,
    progress,
    reportError,
    reports,
    reset,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useReportsStore, import.meta.hot));
