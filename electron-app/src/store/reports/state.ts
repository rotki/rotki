import {
  EventEntry,
  TradeHistoryOverview,
  tradeHistoryPlaceholder
} from '@/model/trade-history-types';

export interface TaxReportState {
  overview: TradeHistoryOverview;
  events: EventEntry[];
  loaded: boolean;
}

export const createTaxReportState = (): TaxReportState => ({
  overview: tradeHistoryPlaceholder(),
  events: [],
  loaded: false
});

export const state: TaxReportState = createTaxReportState();
