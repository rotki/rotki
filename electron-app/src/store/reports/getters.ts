import { GetterTree } from 'vuex';
import { RotkehlchenState } from '@/store/store';
import { TaxReportState } from '@/store/reports/state';
import { SessionState } from '@/store/session/state';

export const getters: GetterTree<TaxReportState, RotkehlchenState> = {
  progress: (state: TaxReportState) => {
    const { historyStart, historyEnd, historyProcess } = state;
    const percentage =
      (historyProcess - historyStart) * (1 / (historyEnd - historyStart));
    return (percentage * 100).toFixed(2);
  }
};
