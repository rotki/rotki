import { computed } from '@vue/composition-api';
import { BigNumber } from 'bignumber.js';
import { useStore } from '@/store/utils';

export const setupGeneralStatistics = () => {
  const store = useStore();

  const totalNetWorthUsd = computed(() => {
    return store.getters['statistics/totalNetWorthUsd'] as BigNumber;
  });

  const fetchNetValue = async () => {
    await store.dispatch('statistics/fetchNetValue');
  };

  return {
    totalNetWorthUsd,
    fetchNetValue
  };
};
