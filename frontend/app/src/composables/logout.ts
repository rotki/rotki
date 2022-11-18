import { useMonitorStore } from '@/store/monitor';
import { resetState } from '@/store/plugins';
import { useSessionAuthStore } from '@/store/session/auth';

export const useSessionStateCleaner = () => {
  const { logged } = storeToRefs(useSessionAuthStore());
  const { start, stop } = useMonitorStore();

  watch(logged, (logged, wasLogged) => {
    if (logged) {
      if (!wasLogged) {
        start();
      }
      return;
    }
    stop();
    resetState();
  });
};
