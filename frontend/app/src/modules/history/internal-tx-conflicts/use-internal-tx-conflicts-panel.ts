import type { Ref } from 'vue';

/**
 * Shared UI state for the pinned internal-tx-conflicts panel. The settings toggle
 * lives on the rail's tab strip (`InternalTxConflictsActions`) but the settings
 * form renders in the panel body, so both read the same flag.
 */
export const useInternalTxConflictsPanel = createSharedComposable((): { showSettings: Ref<boolean> } => {
  const showSettings = ref<boolean>(false);
  return { showSettings };
});
