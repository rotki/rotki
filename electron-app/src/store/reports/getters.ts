import { GetterTree } from 'vuex';
import { RotkehlchenState } from '@/store/store';
import { TaxReportState } from '@/store/reports/state';

export const getters: GetterTree<TaxReportState, RotkehlchenState> = {
  progress: (state: TaxReportState) => {
    const { historyStart, historyEnd, historyProcess } = state;
    const percentage =
      (historyProcess - historyStart) * (1 / (historyEnd - historyStart));
    console.log({
      historyProcess,
      historyStart,
      historyEnd
    });
    return (percentage * 100).toFixed(2);
  }
};
