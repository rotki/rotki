import type { ActionStatus } from '@/types/action';
import type { CollectionResponse } from '@/types/collection';
import { omit } from 'es-toolkit';
import { api } from '@/modules/api/rotki-api';
import {
  type ProfitLossEvent,
  ProfitLossEventsCollectionResponse,
  type ProfitLossEventsPayload,
  type ProfitLossOverview,
  type ProfitLossReportDebugPayload,
  ProfitLossReportOverview,
  type ProfitLossReportPeriod,
  ReportActionableItem,
  Reports,
} from '@/types/reports';
import { type PendingTask, PendingTaskSchema } from '@/types/task';
import { downloadFileByUrl } from '@/utils/download';

interface UseReportsApi {
  generateReport: ({ end, start }: ProfitLossReportPeriod) => Promise<PendingTask>;
  exportReportCSV: (directoryPath: string) => Promise<boolean>;
  downloadReportCSV: () => Promise<ActionStatus>;
  importReportData: (filepath: string) => Promise<PendingTask>;
  exportReportData: (payload: ProfitLossReportDebugPayload) => Promise<PendingTask>;
  uploadReportData: (filepath: File) => Promise<PendingTask>;
  fetchActionableItems: () => Promise<ReportActionableItem>;
  fetchReports: () => Promise<Reports>;
  fetchReport: (reportId: number) => Promise<ProfitLossOverview>;
  fetchReportEvents: (payload: ProfitLossEventsPayload) => Promise<CollectionResponse<ProfitLossEvent>>;
  deleteReport: (reportId: number) => Promise<boolean>;
}

export function useReportsApi(): UseReportsApi {
  const generateReport = async ({ end, start }: ProfitLossReportPeriod): Promise<PendingTask> => {
    const response = await api.get<PendingTask>('/history', {
      query: {
        asyncQuery: true,
        fromTimestamp: start,
        toTimestamp: end,
      },
    });
    return PendingTaskSchema.parse(response);
  };

  const exportReportCSV = async (directoryPath: string): Promise<boolean> => api.get<boolean>('/history/export', {
    query: { directoryPath },
  });

  const downloadReportCSV = async (): Promise<ActionStatus> => {
    try {
      const blob = await api.fetchBlob('/history/download', {
        method: 'GET',
      });

      const url = window.URL.createObjectURL(blob);
      downloadFileByUrl(url, 'reports.zip');
      return { success: true };
    }
    catch (error: any) {
      return { message: error.message, success: false };
    }
  };

  const exportReportData = async (payload: ProfitLossReportDebugPayload): Promise<PendingTask> => {
    const response = await api.post<PendingTask>(
      '/history/debug',
      {
        asyncQuery: true,
        ...payload,
      },
    );
    return PendingTaskSchema.parse(response);
  };

  const importReportData = async (filepath: string): Promise<PendingTask> => {
    const response = await api.put<PendingTask>(
      '/history/debug',
      {
        asyncQuery: true,
        filepath,
      },
    );
    return PendingTaskSchema.parse(response);
  };

  const uploadReportData = async (filepath: File): Promise<PendingTask> => {
    const data = new FormData();
    data.append('filepath', filepath);
    data.append('async_query', 'true');
    const response = await api.patch<PendingTask>('/history/debug', data, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return PendingTaskSchema.parse(response);
  };

  const fetchActionableItems = async (): Promise<ReportActionableItem> => {
    const response = await api.get<ReportActionableItem>('/history/actionable_items');
    return ReportActionableItem.parse(response);
  };

  const fetchReports = async (): Promise<Reports> => {
    const response = await api.get<Reports>('/reports');
    return Reports.parse(response);
  };

  const fetchReport = async (reportId: number): Promise<ProfitLossOverview> => {
    const response = await api.get<ProfitLossReportOverview>(`/reports/${reportId}`);
    const overview = ProfitLossReportOverview.parse(response);
    return overview.entries[0];
  };

  const fetchReportEvents = async (
    payload: ProfitLossEventsPayload,
  ): Promise<CollectionResponse<ProfitLossEvent>> => {
    const response = await api.post<CollectionResponse<ProfitLossEvent>>(
      `/reports/${payload.reportId}/data`,
      omit(payload, ['reportId']),
    );
    return ProfitLossEventsCollectionResponse.parse(response);
  };

  const deleteReport = async (reportId: number): Promise<boolean> => api.delete<boolean>(`/reports/${reportId}`);

  return {
    deleteReport,
    downloadReportCSV,
    exportReportCSV,
    exportReportData,
    fetchActionableItems,
    fetchReport,
    fetchReportEvents,
    fetchReports,
    generateReport,
    importReportData,
    uploadReportData,
  };
}
