import { NetValue } from '@rotki/common/lib/statistics';
import { StatisticsState } from '@/store/statistics/types';

const defaultNetValue: () => NetValue = () => ({
  times: [],
  data: []
});

export const defaultState = (): StatisticsState => ({
  netValue: defaultNetValue()
});

export const state: StatisticsState = defaultState();
