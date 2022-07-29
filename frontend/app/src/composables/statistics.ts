import { BigNumber } from '@rotki/common';
import { Ref } from '@vue/composition-api';
import { storeToRefs } from 'pinia';
import { useStatisticsStore } from '@/store/statistics';

export const setupGeneralStatistics = () => {
  const store = useStatisticsStore();
  const { totalNetWorthUsd } = storeToRefs(store);
  const { fetchNetValue } = store;

  return {
    totalNetWorthUsd: totalNetWorthUsd as Ref<BigNumber>,
    fetchNetValue
  };
};
