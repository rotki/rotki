import { currencies } from '@/data/currencies';
import {
  emptyError,
  emptyPeriod,
  tradeHistoryPlaceholder
} from '@/store/reports/const';
import {
  ProfitLossEvent,
  ProfitLossOverviewData,
  ReportError,
  ReportPeriod,
  ReportProgress
} from '@/store/reports/types';

import { AccountingSettings } from '@/types/user';

export interface ReportState {
  firstProcessedTimestamp: number;
  processed: number;
  limit: number;
  overview: ProfitLossOverviewData;
  events: ProfitLossEvent[];
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
