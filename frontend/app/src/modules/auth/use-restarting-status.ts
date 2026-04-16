import type { Ref } from 'vue';

interface UseRestartingStatusReturn {
  restarting: Ref<boolean>;
}

export const useRestartingStatus = createSharedComposable((): UseRestartingStatusReturn => {
  const restarting = ref<boolean>(false);

  return { restarting };
});
