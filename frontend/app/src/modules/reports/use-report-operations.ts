import type { MaybeRef } from 'vue';
import type { AddressBookSimplePayload } from '@/modules/accounts/address-book/eth-names';
import type { Collection, CollectionResponse } from '@/modules/core/common/collection';
import type { ProfitLossEvent, ProfitLossEventsPayload } from '@/modules/reports/report-types';
import { Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useEnsOperations } from '@/modules/accounts/address-book/use-ens-operations';
import { isBlockchain } from '@/modules/core/common/chains';
import { mapCollectionResponse } from '@/modules/core/common/data/collection-utils';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { getEthAddressesFromText } from '@/modules/history/history-utils';
import { isTransactionEvent } from '@/modules/reports/report-utils';
import { useReportsApi } from '@/modules/reports/use-reports-api';
import { defaultReportEvents, useReportsStore } from '@/modules/reports/use-reports-store';

interface UseReportOperationsReturn {
  createCsv: (reportId: number, path: string) => Promise<void>;
  deleteReport: (reportId: number) => Promise<void>;
  fetchReportEvents: (payload: MaybeRef<ProfitLossEventsPayload>) => Promise<Collection<ProfitLossEvent>>;
  fetchReports: () => Promise<void>;
  getActionableItems: () => Promise<void>;
}

export function useReportOperations(): UseReportOperationsReturn {
  const { notifyError, showErrorMessage, showSuccessMessage } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });
  const { fetchEnsNames } = useEnsOperations();

  const { actionableItems, reports } = storeToRefs(useReportsStore());

  const {
    deleteReport: deleteReportCaller,
    exportReportCSV,
    fetchActionableItems,
    fetchReportEvents: fetchReportEventsCaller,
    fetchReports: fetchReportsCaller,
  } = useReportsApi();

  async function createCsv(reportId: number, path: string): Promise<void> {
    try {
      const success = await exportReportCSV(reportId, path);
      if (success)
        showSuccessMessage(t('actions.reports.csv_export.title'), t('actions.reports.csv_export.message.success'));
      else
        showErrorMessage(t('actions.reports.csv_export.title'), t('actions.reports.csv_export.message.failure'));
    }
    catch (error: unknown) {
      showErrorMessage(t('actions.reports.csv_export.title'), getErrorMessage(error));
    }
  }

  async function fetchReports(): Promise<void> {
    try {
      set(reports, await fetchReportsCaller());
    }
    catch (error: unknown) {
      logger.error(error);
      notifyError(t('actions.reports.fetch.error.title'), t('actions.reports.fetch.error.description'));
    }
  }

  async function deleteReport(reportId: number): Promise<void> {
    try {
      await deleteReportCaller(reportId);
      await fetchReports();
    }
    catch (error: unknown) {
      logger.error(error);
      notifyError(t('actions.reports.delete.error.title'), t('actions.reports.delete.error.description'));
    }
  }

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

  async function fetchReportEvents(payload: MaybeRef<ProfitLossEventsPayload>): Promise<Collection<ProfitLossEvent>> {
    try {
      const response = await fetchReportEventsCaller(get(payload));
      const events = mapCollectionResponse<ProfitLossEvent, CollectionResponse<ProfitLossEvent>>(response);
      fetchEnsNamesFromTransactions(events);
      return events;
    }
    catch (error: unknown) {
      logger.error(error);
      notifyError(t('actions.report_events.fetch.error.title'), t('actions.report_events.fetch.error.description', { error }));
      return defaultReportEvents();
    }
  }

  async function getActionableItems(): Promise<void> {
    const actionable = await fetchActionableItems();
    set(actionableItems, actionable);
  }

  return {
    createCsv,
    deleteReport,
    fetchReportEvents,
    fetchReports,
    getActionableItems,
  };
}
