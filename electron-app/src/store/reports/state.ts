import {
  EventEntry,
  TradeHistoryOverview,
  tradeHistoryPlaceholder
} from '@/model/trade-history-types';
import { currencies } from '@/data/currencies';

export interface TaxReportState {
  overview: TradeHistoryOverview;
  events: EventEntry[];
  currency: string;
  loaded: boolean;
  historyStart: number;
  historyEnd: number;
  historyProcess: number;
}

export const createTaxReportState = (): TaxReportState => ({
  overview: tradeHistoryPlaceholder(),
  events: [],
  currency: currencies[0].ticker_symbol,
  loaded: false,
  historyStart: -1,
  historyEnd: -1,
  historyProcess: -1
});

export const state: TaxReportState = createTaxReportState();
