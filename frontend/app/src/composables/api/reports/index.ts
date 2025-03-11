import type { ActionStatus } from '@/types/action';
import type { CollectionResponse } from '@/types/collection';
import type { PendingTask } from '@/types/task';
import type { ActionResult } from '@rotki/common';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus, validTaskStatus } from '@/services/utils';
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
import { downloadFileByBlobResponse } from '@/utils/download';
import { omit } from 'es-toolkit';

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
    const response = await api.instance.get<ActionResult<PendingTask>>('/history', {
      params: snakeCaseTransformer({
        asyncQuery: true,
        fromTimestamp: start,
        toTimestamp: end,
      }),
      validateStatus: validStatus,
    });
    return handleResponse(response);
  };

  const exportReportCSV = async (directoryPath: string): Promise<boolean> => {
    const response = await api.instance.get<ActionResult<boolean>>('/history/export', {
      params: snakeCaseTransformer({
        directoryPath,
      }),
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const downloadReportCSV = async (): Promise<ActionStatus> => {
    try {
      const response = await api.instance.get('/history/download', {
        responseType: 'blob',
        validateStatus: validTaskStatus,
      });

      if (response.status === 200) {
        downloadFileByBlobResponse(response, 'reports.zip');
        return { success: true };
      }

      const body = await (response.data as Blob).text();
      const result: ActionResult<null> = JSON.parse(body);

      return { message: result.message, success: false };
    }
    catch (error: any) {
      return { message: error.message, success: false };
    }
  };

  const exportReportData = async (payload: ProfitLossReportDebugPayload): Promise<PendingTask> => {
    const response = await api.instance.post<ActionResult<PendingTask>>(
      '/history/debug',
      snakeCaseTransformer({
        asyncQuery: true,
        ...payload,
      }),
      {
        validateStatus: validStatus,
      },
    );
    return handleResponse(response);
  };

  const importReportData = async (filepath: string): Promise<PendingTask> => {
    const response = await api.instance.put<ActionResult<PendingTask>>(
      '/history/debug',
      snakeCaseTransformer({
        asyncQuery: true,
        filepath,
      }),
      {
        validateStatus: validStatus,
      },
    );
    return handleResponse(response);
  };

  const uploadReportData = async (filepath: File): Promise<PendingTask> => {
    const data = new FormData();
    data.append('filepath', filepath);
    data.append('async_query', 'true');
    const response = await api.instance.patch<ActionResult<PendingTask>>('/history/debug', data, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return handleResponse(response);
  };

  const fetchActionableItems = async (): Promise<ReportActionableItem> => {
    const response = await api.instance.get<ActionResult<ReportActionableItem>>('/history/actionable_items', {
      validateStatus: validStatus,
    });

    const data = handleResponse(response);
    return ReportActionableItem.parse(data);
  };

  const fetchReports = async (): Promise<Reports> => {
    const response = await api.instance.get<ActionResult<Reports>>('/reports', {
      validateStatus: validStatus,
    });
    const data = handleResponse(response);
    return Reports.parse(data);
  };

  const fetchReport = async (reportId: number): Promise<ProfitLossOverview> => {
    const response = await api.instance.get<ActionResult<ProfitLossReportOverview>>(`/reports/${reportId}`, {
      validateStatus: validStatus,
    });
    const data = handleResponse(response);
    const overview = ProfitLossReportOverview.parse(data);
    return overview.entries[0];
  };

  const fetchReportEvents = async (
    payload: ProfitLossEventsPayload,
  ): Promise<CollectionResponse<ProfitLossEvent>> => {
    const response = await api.instance.post<ActionResult<CollectionResponse<ProfitLossEvent>>>(
      `/reports/${payload.reportId}/data`,
      snakeCaseTransformer(omit(payload, ['reportId'])),
      {
        validateStatus: validStatus,
      },
    );
    const data = handleResponse(response);
    return ProfitLossEventsCollectionResponse.parse(data);
  };

  const deleteReport = async (reportId: number): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(`/reports/${reportId}`, {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

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
