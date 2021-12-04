import {
  Report,
  ProfitLossEvent,
  ProfitLossOverviewData,
  ReportError,
  ReportPeriod,
  ReportProgress
} from '@rotki/common/lib/reports';
import { currencies } from '@/data/currencies';
import {
  emptyError,
  emptyPeriod,
  tradeHistoryPlaceholder
} from '@/store/reports/const';

import { AccountingSettings } from '@/types/user';

export interface ReportState {
  firstProcessedTimestamp: number;
  processed: number;
  limit: number;
  overview: ProfitLossOverviewData;
  events: ProfitLossEvent[];
  reportId: number;
  reports: Report[];
  reportsFound: number;
  reportsLimit: number;
  accountingSettings: AccountingSettings | null;
  reportPeriod: ReportPeriod;
  currency: string;
  loaded: boolean;
  progress: ReportProgress;
  reportError: ReportError;
}

export const defaultState = (): ReportState => ({
  overview: tradeHistoryPlaceholder(),
  events: [],
  processed: -1,
  limit: -1,
  reportId: -1,
  reports: [],
  reportsFound: -1,
  reportsLimit: -1,
  firstProcessedTimestamp: -1,
  accountingSettings: null,
  reportPeriod: emptyPeriod(),
  currency: currencies[0].tickerSymbol,
  loaded: false,
  progress: {
    processingState: '',
    totalProgress: ''
  },
  reportError: emptyError()
});

export const state: ReportState = defaultState();
