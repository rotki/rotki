import {
  ReportError,
  ReportPeriod,
  ReportProgress,
  ReportsPayloadData
} from '@rotki/common/lib/reports';
import { MutationTree } from 'vuex';
import { ReportMutations } from '@/store/reports/const';
import { defaultState, ReportState } from '@/store/reports/state';
import { ReportData } from '@/store/reports/types';

import { AccountingSettings } from '@/types/user';

export const mutations: MutationTree<ReportState> = {
  set(state: ReportState, payload: ReportData) {
    const { overview, events, processed, limit, firstProcessedTimestamp } =
      payload;
    state.overview = { ...overview };
    state.events = [...events];
    state.processed = processed;
    state.limit = limit;
    state.loaded = true;
    state.firstProcessedTimestamp = firstProcessedTimestamp;
  },

  [ReportMutations.SET_REPORTS](
    state: ReportState,
    payload: ReportsPayloadData
  ) {
    const { entries, entriesFound, entriesLimit } = payload;
    state.reports = [...entries];
    state.reportsFound = entriesFound;
    state.reportsLimit = entriesLimit;
  },

  [ReportMutations.SET_REPORT_ID](state: ReportState, reportId: number) {
    state.reportId = reportId;
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

  [ReportMutations.PROGRESS](state: ReportState, payload: ReportProgress) {
    state.progress = payload;
  },

  [ReportMutations.REPORT_ERROR](state: ReportState, payload: ReportError) {
    state.reportError = payload;
  },
  reset(state: ReportState) {
    Object.assign(state, defaultState());
  }
};
