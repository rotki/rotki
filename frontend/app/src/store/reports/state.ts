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

import { AccountingSettings } from '@/typing/types';

export interface ReportState {
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
  accountingSettings: null,
  reportPeriod: emptyPeriod(),
  currency: currencies[0].ticker_symbol,
  loaded: false,
  progress: {
    processingState: '',
    totalProgress: ''
  },
  reportError: emptyError()
});

export const state: ReportState = defaultState();
