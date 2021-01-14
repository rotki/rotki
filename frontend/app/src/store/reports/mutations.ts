import { MutationTree } from 'vuex';
import {
  EventEntry,
  ProfitLossOverviewData
} from '@/model/trade-history-types';
import { defaultState, ReportState } from '@/store/reports/state';
import { ReportPeriod } from '@/store/reports/types';
import { AccountingSettings } from '@/typing/types';

export const mutations: MutationTree<ReportState> = {
  set(
    state: ReportState,
    payload: {
      overview: ProfitLossOverviewData;
      events: EventEntry[];
      currency: string;
    }
  ) {
    const { overview, events } = payload;
    state.overview = { ...overview };
    state.events = [...events];
    state.loaded = true;
  },

  currency(state: ReportState, currency: string) {
    state.currency = currency;
  },

  historyProcess(
    state: ReportState,
    payload: { start: number; current: number }
  ) {
    state.historyStart = payload.start;
    state.historyProcess = payload.current;
  },

  reportPeriod(state: ReportState, payload: ReportPeriod) {
    state.historyProcess = payload.start;
    state.historyStart = payload.start;
    state.historyEnd = payload.end;
    state.reportPeriod = payload;
  },

  accountingSettings(state: ReportState, payload: AccountingSettings) {
    state.accountingSettings = payload;
  },

  reset(state: ReportState) {
    Object.assign(state, defaultState());
  }
};
