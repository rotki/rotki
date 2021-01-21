import { currencies } from '@/data/currencies';
import { emptyPeriod, tradeHistoryPlaceholder } from '@/store/reports/const';
import {
  ProfitLossEvent,
  ProfitLossOverviewData,
  ReportPeriod,
  ReportProgress
} from '@/store/reports/types';

import { AccountingSettings } from '@/typing/types';

export interface ReportState {
  overview: ProfitLossOverviewData;
  events: ProfitLossEvent[];
  accountingSettings: AccountingSettings | null;
  reportPeriod: ReportPeriod;
  currency: string;
  loaded: boolean;
  progress: ReportProgress;
}

export const defaultState = (): ReportState => ({
  overview: tradeHistoryPlaceholder(),
  events: [],
  accountingSettings: null,
  reportPeriod: emptyPeriod(),
  currency: currencies[0].ticker_symbol,
  loaded: false,
  progress: {
    processingState: '',
    totalProgress: ''
  }
});

export const state: ReportState = defaultState();
