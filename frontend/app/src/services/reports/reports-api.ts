import { ActionResult } from '@rotki/common/lib/data';
import {
  AxiosInstance,
  AxiosRequestTransformer,
  AxiosResponseTransformer
} from 'axios';
import {
  axiosSnakeCaseTransformer,
  setupTransformer
} from '@/services/axios-tranformers';
import { basicAxiosTransformer } from '@/services/consts';
import { PendingTask } from '@/services/types-api';
import { handleResponse, validStatus } from '@/services/utils';
import {
  ProfitLossOverview,
  ProfitLossReportEvents,
  ProfitLossReportOverview,
  ProfitLossReportPeriod,
  Reports
} from '@/types/reports';

export class ReportsApi {
  private readonly axios: AxiosInstance;
  private readonly responseTransformer: AxiosResponseTransformer[] =
    setupTransformer([]);
  private readonly requestTransformer: AxiosRequestTransformer[];

  constructor(axios: AxiosInstance) {
    this.axios = axios;
    this.responseTransformer = axios.defaults
      .transformResponse as AxiosResponseTransformer[];
    this.requestTransformer = [axiosSnakeCaseTransformer].concat(
      axios.defaults.transformRequest as AxiosRequestTransformer[]
    );
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
