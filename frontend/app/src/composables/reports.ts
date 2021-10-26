import { computed } from '@vue/composition-api';
import { useStore } from '@/store/utils';

export const setupReports = () => {
  const store = useStore();
  const progress = computed<string>(() => store.getters['reports/progress']);
  return {
    progress
  };
};
