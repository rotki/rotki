import { ProfitLossEvent, ProfitLossOverviewData } from '@/types/reports';

export type ReportData = {
  readonly overview: ProfitLossOverviewData;
  readonly events: ProfitLossEvent[];
  readonly limit: number;
  readonly processed: number;
  readonly firstProcessedTimestamp: number;
};
