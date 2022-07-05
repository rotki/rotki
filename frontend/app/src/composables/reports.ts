import { computed } from 'vue';
import { useStore } from '@/store/utils';

export const setupReports = () => {
  const store = useStore();
  const progress = computed<string>(() => store.getters['reports/progress']);
  return {
    progress
  };
};
