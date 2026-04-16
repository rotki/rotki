import { startPromise } from '@shared/utils';
import { usePasswordConfirmation } from '@/modules/auth/use-password-confirmation';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useIntervalScheduler } from './use-interval-scheduler';

const PASSWORD_CHECK_MS = 60 * 60 * 1_000;

interface UsePasswordCheckSchedulerReturn {
  start: () => void;
  stop: () => void;
}

export function usePasswordCheckScheduler(): UsePasswordCheckSchedulerReturn {
  const { logged, username } = storeToRefs(useSessionAuthStore());
  const { checkIfPasswordConfirmationNeeded } = usePasswordConfirmation();

  const scheduler = useIntervalScheduler({
    callback(): void {
      if (!get(logged))
        return;

      const currentUsername = get(username);
      if (!currentUsername)
        return;

      startPromise(checkIfPasswordConfirmationNeeded(currentUsername));
    },
    intervalMs: PASSWORD_CHECK_MS,
  });

  return {
    start: scheduler.start,
    stop: scheduler.stop,
  };
}
