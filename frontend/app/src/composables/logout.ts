import { resetState } from '@/store/plugins';
import { useSessionStore } from '@/store/session';

export const useSessionStateCleaner = () => {
  const { logged } = storeToRefs(useSessionStore());

  watch(logged, logged => {
    if (logged) {
      return;
    }

    resetState();
  });
};
