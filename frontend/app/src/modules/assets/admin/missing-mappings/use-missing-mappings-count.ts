import type { Ref } from 'vue';
import { useMissingMappingsDB } from '@/modules/assets/admin/missing-mappings/use-missing-mappings-db';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { logger } from '@/modules/core/common/logging/logging';

interface UseMissingMappingsCountReturn {
  /** How many exchange assets are waiting for a mapping, as of the last read. */
  count: Readonly<Ref<number>>;
  /** Re-reads the count from the local table. */
  refresh: () => Promise<void>;
}

/**
 * The number of exchange assets rotki could not map, shared by whatever adds to or takes from the
 * table and whatever shows the number.
 *
 * @remarks
 * The table is a local browser store with no change feed, so every writer refreshes this after its
 * write. It belongs to the logged in user, so it goes back to zero on logout.
 */
export const useMissingMappingsCount = createSharedComposable((): UseMissingMappingsCountReturn => {
  const { count: countMappings } = useMissingMappingsDB();
  const { logged } = storeToRefs(useSessionAuthStore());

  const count = shallowRef<number>(0);

  async function refresh(): Promise<void> {
    try {
      set(count, await countMappings());
    }
    catch (error: unknown) {
      logger.error(error);
    }
  }

  watch(logged, (isLogged) => {
    if (!isLogged)
      set(count, 0);
  });

  return {
    count: readonly(count),
    refresh,
  };
});
