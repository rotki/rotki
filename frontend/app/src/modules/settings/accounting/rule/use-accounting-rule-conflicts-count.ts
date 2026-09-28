import type { Ref } from 'vue';
import { pipe } from 'plainfp';
import { getOr, map, type Result, tapError } from 'plainfp/result';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { isRequestFailure, type RequestError } from '@/modules/core/api/request-result';
import { logger } from '@/modules/core/common/logging/logging';
import { useAccountingSettings } from '@/modules/settings/accounting/use-accounting-settings';

interface UseAccountingRuleConflictsCountReturn {
  /** How many accounting rules conflict with their remote version, as of the last read. */
  count: Readonly<Ref<number>>;
  /**
   * Re-reads the count, keeping the last known one when the read fails rather than claiming there
   * are no conflicts. The failure is logged, not notified, and handed back.
   */
  refresh: () => Promise<Result<number, RequestError>>;
}

/**
 * The number of conflicting accounting rules, shared by the accounting rules page and the action
 * center.
 *
 * @remarks
 * The rules belong to the logged in user, so the count goes back to zero on logout.
 */
export const useAccountingRuleConflictsCount = createSharedComposable((): UseAccountingRuleConflictsCountReturn => {
  const { getAccountingRulesConflicts } = useAccountingSettings();
  const { logged } = storeToRefs(useSessionAuthStore());

  const count = shallowRef<number>(0);

  async function refresh(): Promise<Result<number, RequestError>> {
    const recount = pipe(
      await getAccountingRulesConflicts({ limit: 1, offset: 0 }),
      map(conflicts => conflicts.total),
      tapError((error) => {
        if (isRequestFailure(error))
          logger.error(error.cause);
      }),
    );
    set(count, getOr(recount, get(count)));
    return recount;
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
