import { MutationTree } from 'vuex';
import {
  MUTATION_PROGRESS,
  MUTATION_REPORT_ERROR
} from '@/store/reports/const';
import { defaultState, ReportState } from '@/store/reports/state';
import {
  ReportData,
  ReportError,
  ReportPeriod,
  ReportProgress
} from '@/store/reports/types';

import { AccountingSettings } from '@/typing/types';

export const mutations: MutationTree<ReportState> = {
  set(state: ReportState, payload: ReportData) {
    const {
      overview,
      events,
      processed,
      limit,
      firstProcessedTimestamp
    } = payload;
    state.overview = { ...overview };
    state.events = [...events];
    state.processed = processed;
    state.limit = limit;
    state.loaded = true;
    state.firstProcessedTimestamp = firstProcessedTimestamp;
  },

  currency(state: ReportState, currency: string) {
    state.currency = currency;
  },

  reportPeriod(state: ReportState, payload: ReportPeriod) {
    state.reportPeriod = payload;
  },

  accountingSettings(state: ReportState, payload: AccountingSettings) {
    state.accountingSettings = payload;
  },

  [MUTATION_PROGRESS](state: ReportState, payload: ReportProgress) {
    state.progress = payload;
  },

  [MUTATION_REPORT_ERROR](state: ReportState, payload: ReportError) {
    state.reportError = payload;
  },
  reset(state: ReportState) {
    Object.assign(state, defaultState());
  }
};
