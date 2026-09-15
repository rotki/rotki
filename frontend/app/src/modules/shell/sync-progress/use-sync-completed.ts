import type { Ref } from 'vue';
import { useSyncRollup } from '@/modules/history/events/tx/use-sync-rollup';

interface UseSyncCompletedReturn {
  /** Bumped once each time the aggregate history sync finishes; watch it to react. */
  syncCompleted: Ref<number>;
}

/**
 * Emits a signal every time the aggregate history sync (tx query + exchange events +
 * decoding) settles. Shared so any number of consumers react off a single, centrally
 * checked completion instead of each watching the refresh themselves.
 */
export const useSyncCompleted = createSharedComposable((): UseSyncCompletedReturn => {
  const { isSettled } = useSyncRollup();
  const syncCompleted = ref<number>(0);

  watch(isSettled, (settled) => {
    if (settled)
      set(syncCompleted, get(syncCompleted) + 1);
  });

  return { syncCompleted };
});
