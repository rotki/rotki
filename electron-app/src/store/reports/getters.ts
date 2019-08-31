import { GetterTree } from 'vuex';
import { RotkehlchenState } from '@/store/store';
import { TaxReportState } from '@/store/reports/state';

export const getters: GetterTree<TaxReportState, RotkehlchenState> = {
  progress: (state: TaxReportState) => {
    const { historyStart, historyEnd, historyProcess } = state;
    const process = historyProcess >= 0 ? historyProcess : historyStart;
    const percentage =
      ((process - historyStart) * 100) / (historyEnd - historyStart);
    return percentage.toFixed(2);
  }
};
