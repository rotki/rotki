import type { ComputedRef, Ref } from 'vue';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseAccountLoadingReturn {
  pending: Ref<boolean>;
  loading: ComputedRef<boolean>;
  isAccountOperationRunning: (blockchain?: string) => ComputedRef<boolean>;
}

export const useAccountLoading = createSharedComposable((): UseAccountLoadingReturn => {
  const pending = ref<boolean>(false);

  const { useWorkStatus, useWorkStatusPrefix } = useTaskCenter();
  const { isRefreshing } = storeToRefs(useBalanceRefreshState());

  // With a blockchain, gate on that chain's exact add/remove activity; without, aggregate over all.
  const isAccountOperationRunning = (blockchain?: string): ComputedRef<boolean> => {
    const add = blockchain
      ? useWorkStatus(ActivityKind.ACCOUNTS, ActivityPart.ADD, blockchain)
      : useWorkStatusPrefix(ActivityKind.ACCOUNTS, ActivityPart.ADD);
    const remove = blockchain
      ? useWorkStatus(ActivityKind.ACCOUNTS, ActivityPart.REMOVE, blockchain)
      : useWorkStatusPrefix(ActivityKind.ACCOUNTS, ActivityPart.REMOVE);
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
