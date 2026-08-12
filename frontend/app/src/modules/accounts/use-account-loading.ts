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

  // A chain is a *prefix* of an add/remove key, never a whole one — the id also carries what is
  // being acted on. `partsWithin` is what encodes that: it takes the leading slice of the key, so
  // the coarse read cannot drift from the ids the producers actually submit.
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
