import { computed } from '@vue/composition-api';
import { BigNumber } from 'bignumber.js';
import { useStore } from '@/store/utils';

export const totalNetWorthUsd = computed(() => {
  const store = useStore();
  return store.getters['statistics/totalNetWorthUsd'] as BigNumber;
});
