import type { Ref } from 'vue';

interface UseRestartingStatusReturn {
  /** Whether a backend restart is under way. */
  restarting: Ref<boolean>;
}

/**
 * Shares "a restart is under way" between the unlock flow, which knows it, and the connection
 * screen, which does not.
 *
 * @remarks
 * The backend connection does drop while it restarts, so without this the connection screen reports
 * a lost connection for something that is going exactly to plan.
 */
export const useRestartingStatus = createSharedComposable((): UseRestartingStatusReturn => {
  const restarting = ref<boolean>(false);

  return { restarting };
});
