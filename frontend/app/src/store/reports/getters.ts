import { GetterTree } from 'vuex';
import { ReportState } from '@/store/reports/state';
import { RotkehlchenState } from '@/store/types';

export const getters: GetterTree<ReportState, RotkehlchenState> = {
  progress: ({ progress: { totalProgress } }: ReportState) => totalProgress,
  processingState: ({ progress: { processingState } }: ReportState) =>
    processingState
};
