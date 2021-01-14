import { currencies } from '@/data/currencies';
import {
  EventEntry,
  ProfitLossOverviewData,
  tradeHistoryPlaceholder
} from '@/model/trade-history-types';
import { emptyPeriod } from '@/store/reports/const';
import { ReportPeriod } from '@/store/reports/types';
import { AccountingSettings } from '@/typing/types';

export interface ReportState {
  overview: ProfitLossOverviewData;
  events: EventEntry[];
  accountingSettings: AccountingSettings | null;
  reportPeriod: ReportPeriod;
  currency: string;
  loaded: boolean;
  historyStart: number;
  historyEnd: number;
  historyProcess: number;
}

export const defaultState = (): ReportState => ({
  overview: tradeHistoryPlaceholder(),
  events: [],
  accountingSettings: null,
  reportPeriod: emptyPeriod(),
  currency: currencies[0].ticker_symbol,
  loaded: false,
  historyStart: -1,
  historyEnd: -1,
  historyProcess: -1
});

export const state: ReportState = defaultState();
