import { ActionResult } from '@rotki/common/lib/data';
import {
  ReportEventsPayloadData,
  ReportOverviewPayloadData,
  ReportsPayloadData
} from '@rotki/common/lib/reports';
import {
  AxiosInstance,
  AxiosResponseTransformer,
  AxiosRequestTransformer
} from 'axios';
import {
  axiosSnakeCaseTransformer,
  setupTransformer
} from '@/services/axios-tranformers';
import { reportNumericKeys } from '@/services/reports/const';
import { handleResponse, validStatus } from '@/services/utils';

export class ReportsApi {
  private readonly axios: AxiosInstance;
  private readonly responseTransformer: AxiosResponseTransformer[] =
    setupTransformer(reportNumericKeys);
  private readonly requestTransformer: AxiosRequestTransformer[];

  constructor(axios: AxiosInstance) {
    this.axios = axios;
    this.responseTransformer = axios.defaults
      .transformResponse as AxiosResponseTransformer[];
    this.requestTransformer = [axiosSnakeCaseTransformer].concat(
      axios.defaults.transformRequest as AxiosRequestTransformer[]
    );
  }

  fetchReports(): Promise<ReportsPayloadData> {
    return this.axios
      .get<ActionResult<ReportsPayloadData>>('/reports', {
        validateStatus: validStatus,
        transformResponse: setupTransformer(reportNumericKeys)
      })
      .then(handleResponse)
      .then(result => ReportsPayloadData.parse(result));
  }

  fetchReportOverview(reportId: number): Promise<ReportOverviewPayloadData> {
    return this.axios
      .get<ActionResult<ReportOverviewPayloadData>>(
        `/reports/${reportId}/data/accounting_overview`,
        {
          validateStatus: validStatus,
          transformResponse: setupTransformer(reportNumericKeys)
        }
      )
      .then(handleResponse)
      .then(result => ReportOverviewPayloadData.parse(result));
  }

  fetchReportEvents(reportId: number): Promise<ReportEventsPayloadData> {
    return this.axios
      .post<ActionResult<ReportEventsPayloadData>>(
        `/reports/${reportId}/data/`,
        {
          validateStatus: validStatus,
          transformResponse: setupTransformer(reportNumericKeys)
        }
      )
      .then(handleResponse)
      .then(result => ReportEventsPayloadData.parse(result));
  }

  deleteReport(reportId: number): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>(`/reports/${reportId}`, {
        validateStatus: validStatus,
        transformResponse: setupTransformer(reportNumericKeys)
      })
      .then(handleResponse);
  }
}
