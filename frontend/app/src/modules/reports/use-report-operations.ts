import type { MaybeRef } from 'vue';
import type { Collection, CollectionResponse } from '@/modules/core/common/collection';
import type { ProfitLossEvent, ProfitLossEventsPayload } from '@/modules/reports/report-types';
import { get, set } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { pipe } from 'plainfp';
import { type ResultAsync, tap } from 'plainfp/result-async';
import { useI18n } from 'vue-i18n';
import { fromRequest, type RequestError } from '@/modules/core/api/request-result';
import { mapCollectionResponse } from '@/modules/core/common/data/collection-utils';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { useReportEnsNames } from '@/modules/reports/use-report-ens-names';
import { useReportsApi } from '@/modules/reports/use-reports-api';
import { useReportsStore } from '@/modules/reports/use-reports-store';

interface UseReportOperationsReturn {
  createCsv: (reportId: number, path: string) => Promise<void>;
  deleteReport: (reportId: number) => Promise<void>;
  fetchReportEvents: (payload: MaybeRef<ProfitLossEventsPayload>) => ResultAsync<Collection<ProfitLossEvent>, RequestError>;
  fetchReports: () => Promise<void>;
  getActionableItems: () => Promise<void>;
}

export function useReportOperations(): UseReportOperationsReturn {
  const { notifyError, notifyFailure, notifyInfo } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });
  const { fetchEnsNamesFromTransactions } = useReportEnsNames();

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
        notifyInfo(t('actions.reports.csv_export.title'), t('actions.reports.csv_export.message.success'));
      else
        notifyError(t('actions.reports.csv_export.title'), t('actions.reports.csv_export.message.failure'));
    }
    catch (error: unknown) {
      notifyError(t('actions.reports.csv_export.title'), getErrorMessage(error));
    }
  }

  async function fetchReports(): Promise<void> {
    try {
      set(reports, await fetchReportsCaller());
    }
    catch (error: unknown) {
      logger.error(error);
      notifyFailure(t('actions.reports.fetch.error.title'), t('actions.reports.fetch.error.description'));
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

  async function fetchReportEvents(payload: MaybeRef<ProfitLossEventsPayload>): ResultAsync<Collection<ProfitLossEvent>, RequestError> {
    return pipe(
      fromRequest(async () => mapCollectionResponse<ProfitLossEvent, CollectionResponse<ProfitLossEvent>>(
        await fetchReportEventsCaller(get(payload)),
      )),
      tap(fetchEnsNamesFromTransactions),
    );
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
