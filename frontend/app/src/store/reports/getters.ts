import { GetterTree } from 'vuex';
import { ReportState } from '@/store/reports/state';
import { RotkehlchenState } from '@/store/types';

export const getters: GetterTree<ReportState, RotkehlchenState> = {
  progress: (state: ReportState) => {
    const { historyStart, historyEnd, historyProcess } = state;
    const percentage =
      (historyProcess - historyStart) * (1 / (historyEnd - historyStart));
    return (percentage * 100).toFixed(2);
  }
};
