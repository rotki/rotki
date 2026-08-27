import type { ComputedRef, Ref } from 'vue';
import { accountAddActivity, accountRemoveActivity } from '@/modules/accounts/accounts.activity';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseAccountLoadingReturn {
  pending: Ref<boolean>;
  loading: ComputedRef<boolean>;
  isAccountOperationRunning: (blockchain?: string) => ComputedRef<boolean>;
}

export const useAccountLoading = createSharedComposable((): UseAccountLoadingReturn => {
  const pending = ref<boolean>(false);

  const { useWorkStatusPrefix } = useTaskCenter();
  const { isRefreshing } = storeToRefs(useBalanceRefreshState());

  /**
   * Tracks whether an account addition or removal is in flight.
   *
   * @remarks
   * A chain is only the leading slice of an add/remove activity key, so matching is by prefix and
   * `partsWithin` builds that prefix from the activity definition rather than from a literal here.
   * @param blockchain - narrows the match to one chain; omitting it covers every chain
   */
  const isAccountOperationRunning = (blockchain?: string): ComputedRef<boolean> => {
    const within = blockchain ? ([blockchain] as const) : ([] as const);
    const add = useWorkStatusPrefix(accountAddActivity.kind, ...accountAddActivity.partsWithin(within));
    const remove = useWorkStatusPrefix(accountRemoveActivity.kind, ...accountRemoveActivity.partsWithin(within));
    return logicOr(
      computed<boolean>(() => get(add).active),
      computed<boolean>(() => get(remove).active),
    );
  };

  const loading: ComputedRef<boolean> = logicOr(isAccountOperationRunning(), pending, isRefreshing);

  return {
    isAccountOperationRunning,
    loading,
    pending,
  };
});
