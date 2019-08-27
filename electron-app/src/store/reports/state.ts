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
  historyProcess: number;
}

export const createTaxReportState = (): TaxReportState => ({
  overview: tradeHistoryPlaceholder(),
  events: [],
  currency: currencies[0].ticker_symbol,
  loaded: false,
  historyProcess: -1
});

export const state: TaxReportState = createTaxReportState();
