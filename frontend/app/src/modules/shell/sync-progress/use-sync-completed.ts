import type { Ref } from 'vue';
import { SyncPhase } from '@/modules/shell/sync-progress/types';
import { useSyncProgress } from '@/modules/shell/sync-progress/use-sync-progress';

interface UseSyncCompletedReturn {
  /** Bumped once each time the aggregate history sync finishes; watch it to react. */
  syncCompleted: Ref<number>;
}

/**
 * Emits a signal every time the aggregate history sync (tx query + exchange events +
 * decoding) transitions to complete. Shared so any number of consumers react off a
 * single, centrally checked completion instead of each watching the sync phase itself.
 */
export const useSyncCompleted = createSharedComposable((): UseSyncCompletedReturn => {
  const { phase } = useSyncProgress();
  const syncCompleted = ref<number>(0);

  watch(phase, (current) => {
    if (current === SyncPhase.COMPLETE)
      set(syncCompleted, get(syncCompleted) + 1);
  });

  return { syncCompleted };
});
