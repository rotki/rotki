import { NetValue } from '@/services/types-api';
import { StatisticsState } from '@/store/statistics/types';

const defaultNetValue: () => NetValue = () => ({
  times: [],
  data: []
});

export const defaultState = (): StatisticsState => ({
  netValue: defaultNetValue()
});

export const state: StatisticsState = defaultState();
