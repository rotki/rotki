import { ActionResult } from '@rotki/common/lib/data';
import { AxiosInstance } from 'axios';
import {
  axiosSnakeCaseTransformer,
  setupTransformer
} from '@/services/axios-tranformers';
import { basicAxiosTransformer } from '@/services/consts';
import { PendingTask } from '@/services/types-api';
import { handleResponse, validStatus } from '@/services/utils';
import {
  ProfitLossOverview,
  ProfitLossReportDebugPayload,
  ProfitLossReportEvents,
  ProfitLossReportOverview,
  ProfitLossReportPeriod,
  ReportActionableItem,
  Reports
} from '@/types/reports';

export class ReportsApi {
  private readonly axios: AxiosInstance;

  constructor(axios: AxiosInstance) {
    this.axios = axios;
  }

  async generateReport({
    end,
    start
  }: ProfitLossReportPeriod): Promise<PendingTask> {
    const response = await this.axios.get<ActionResult<PendingTask>>(
      '/history/',
      {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true,
          fromTimestamp: start,
          toTimestamp: end
        }),
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );
    return handleResponse(response);
  }

  async exportReportData(
    payload: ProfitLossReportDebugPayload
  ): Promise<PendingTask> {
    const response = await this.axios.post<ActionResult<PendingTask>>(
      '/history/debug',
      axiosSnakeCaseTransformer({
        asyncQuery: true,
        ...payload
      }),
      {
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );
    return handleResponse(response);
  }

  async importReportData(filepath: string): Promise<PendingTask> {
    const response = await this.axios.put<ActionResult<PendingTask>>(
      '/history/debug',
      axiosSnakeCaseTransformer({
        filepath,
        asyncQuery: true
      }),
      {
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );
    return handleResponse(response);
  }

  async uploadReportData(filepath: File): Promise<PendingTask> {
    const data = new FormData();
    data.append('filepath', filepath);
    const response = await this.axios.post<ActionResult<PendingTask>>(
      '/history/debug?async_query=true',
      data,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    );

    return handleResponse(response);
  }

  async fetchActionableItems(): Promise<ReportActionableItem> {
    const response = await this.axios.get<ActionResult<ReportActionableItem>>(
      '/history/actionable_items',
      {
        validateStatus: validStatus,
        transformResponse: setupTransformer([])
      }
    );

    const data = handleResponse(response);
    return ReportActionableItem.parse(data);
  }

  async fetchReports(): Promise<Reports> {
    const response = await this.axios.get<ActionResult<Reports>>('/reports/', {
      validateStatus: validStatus,
      transformResponse: setupTransformer([])
    });
    const data = handleResponse(response);
    return Reports.parse(data);
  }

  async fetchReport(reportId: number): Promise<ProfitLossOverview> {
    const response = await this.axios.get<
      ActionResult<ProfitLossReportOverview>
    >(`/reports/${reportId}`, {
      validateStatus: validStatus,
      transformResponse: setupTransformer([])
    });
    const data = handleResponse(response);
    const overview = ProfitLossReportOverview.parse(data);
    return overview.entries[0];
  }

  async fetchReportEvents(
    reportId: number,
    page: { limit: number; offset: number }
  ): Promise<ProfitLossReportEvents> {
    const response = await this.axios.post<
      ActionResult<ProfitLossReportEvents>
    >(`/reports/${reportId}/data`, page, {
      validateStatus: validStatus,
      transformResponse: setupTransformer([])
    });
    const data = handleResponse(response);
    return ProfitLossReportEvents.parse(data);
  }

  deleteReport(reportId: number): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>(`/reports/${reportId}`, {
        validateStatus: validStatus,
        transformResponse: setupTransformer([])
      })
      .then(handleResponse);
  }
}
