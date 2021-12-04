import {
  ProfitLossEvent,
  ProfitLossOverviewData
} from '@rotki/common/lib/reports';

export type ReportData = {
  readonly overview: ProfitLossOverviewData;
  readonly events: ProfitLossEvent[];
  readonly limit: number;
  readonly processed: number;
  readonly firstProcessedTimestamp: number;
};
