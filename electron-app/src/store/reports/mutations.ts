import { MutationTree } from 'vuex';
import { defaultState, TaxReportState } from '@/store/reports/state';
import { EventEntry, TradeHistoryOverview } from '@/model/trade-history-types';

export const mutations: MutationTree<TaxReportState> = {
  set(
    state: TaxReportState,
    payload: {
      overview: TradeHistoryOverview;
      events: EventEntry[];
      currency: string;
    }
  ) {
    const { overview, events } = payload;
    state.overview = { ...overview };
    state.events = [...events];
    state.loaded = true;
  },

  currency(state: TaxReportState, currency: string) {
    state.currency = currency;
  },

  historyProcess(state: TaxReportState, historyProcess: number) {
    state.historyProcess = historyProcess;
  },

  reportPeriod(state: TaxReportState, payload: { start: number; end: number }) {
    state.historyProcess = payload.start;
    state.historyStart = payload.start;
    state.historyEnd = payload.end;
  },

  reset(state: TaxReportState) {
    state = Object.assign(state, defaultState());
  }
};
