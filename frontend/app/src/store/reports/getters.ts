import { GetterTree } from 'vuex';
import { TaxReportState } from '@/store/reports/state';
import { RotkehlchenState } from '@/store/types';

export const getters: GetterTree<TaxReportState, RotkehlchenState> = {
  progress: (state: TaxReportState) => {
    const { historyStart, historyEnd, historyProcess } = state;
    const percentage =
      (historyProcess - historyStart) * (1 / (historyEnd - historyStart));
    return (percentage * 100).toFixed(2);
  }
};
