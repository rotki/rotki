import { computed } from 'vue';
import { DefiProtocolSummary } from '@/store/defi/types';
import { useStore } from '@/store/utils';

export const useDefi = () => {
  const store = useStore();

  const fetchAll = async (refresh: boolean): Promise<void> => {
    await store.dispatch('defi/fetchAllDefi', refresh);
  };

  const defiOverview = computed<DefiProtocolSummary[]>(() => {
    return store.getters['defi/defiOverview'];
  });

  return {
    defiOverview,
    fetchAll
  };
};
