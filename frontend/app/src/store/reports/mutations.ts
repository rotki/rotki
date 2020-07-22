import { MutationTree } from 'vuex';
import { EventEntry, TradeHistoryOverview } from '@/model/trade-history-types';
import { defaultState, TaxReportState } from '@/store/reports/state';

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

  // historyProcess(state: TaxReportState, historyStart: number, historyProcess: number) {
  historyProcess(
    state: TaxReportState,
    payload: { start: number; current: number }
  ) {
    console.log(
      'Commiting historyProcess payload: ' + JSON.stringify(payload, null, 4)
    );
    // state.historyStart = historyStart;
    // state.historyProcess = historyProcess;
    state.historyStart = payload.start;
    state.historyProcess = payload.current;
  },

  reportPeriod(state: TaxReportState, payload: { start: number; end: number }) {
    state.historyProcess = payload.start;
    state.historyStart = payload.start;
    state.historyEnd = payload.end;
  },

  reset(state: TaxReportState) {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    state = Object.assign(state, defaultState());
  }
};
