import type { ComputedRef } from 'vue';
import { get } from '@vueuse/shared';
import { useSupportedChains } from '@/composables/info/chains';
import { useBalanceQueueStore } from '@/store/balances/balance-queue';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

interface BalanceQueryProgress {
  type: TaskType.FETCH_DETECTED_TOKENS | TaskType.QUERY_BLOCKCHAIN_BALANCES;
  currentStep: number;
  totalSteps: number;
  percentage: number;
  currentOperation: string | null;
  currentOperationData: {
    type: TaskType.FETCH_DETECTED_TOKENS | TaskType.QUERY_BLOCKCHAIN_BALANCES;
    chain?: string;
    address?: string;
    status: string;
  } | null;
}

interface UseBalanceQueryProgressReturn {
  balanceProgress: ComputedRef<BalanceQueryProgress | null>;
  isBalanceQuerying: ComputedRef<boolean>;
}

export function useBalanceQueryProgress(): UseBalanceQueryProgressReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { getChainName } = useSupportedChains();
  const { useIsTaskRunning } = useTaskStore();
  const balanceQueue = useBalanceQueueStore();
  const { completedItems, progress, queueItems, runningItems, totalItems } = storeToRefs(balanceQueue);

  const isBalanceQuerying = logicOr(
    useIsTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES),
    useIsTaskRunning(TaskType.FETCH_DETECTED_TOKENS),
    computed(() => get(runningItems) > 0),
  );

  const balanceProgress = computed<BalanceQueryProgress | null>(() => {
    const items = get(queueItems);
    const total = get(totalItems);
    const completed = get(completedItems);

    if (total === 0) {
      return null;
    }

    // Find current running item
    const runningItem = items.find(item => item.status === 'running');

    if (!runningItem) {
      // No running item but items in queue
      if (items.length > 0) {
        // Show pending status
        const firstPending = items.find(item => item.status === 'pending');
        if (firstPending) {
          const isTokenDetection = firstPending.type === TaskType.FETCH_DETECTED_TOKENS;
          return {
            currentOperation: isTokenDetection
              ? t('dashboard.history_query_indicator.token_detection_status.detecting')
              : t('dashboard.history_query_indicator.balance_status.querying_balances'),
            currentOperationData: {
              address: firstPending.address,
              chain: firstPending.chain,
              status: 'pending',
              type: firstPending.type,
            },
            currentStep: completed,
            percentage: get(progress),
            totalSteps: total,
            type: firstPending.type,
          };
        }
      }
      return null;
    }

    const currentStep = completed + 1;
    const isTokenDetection = runningItem.type === TaskType.FETCH_DETECTED_TOKENS;

    let currentOperation: string;
    let currentOperationData: BalanceQueryProgress['currentOperationData'];

    if (isTokenDetection && runningItem.address) {
      currentOperation = t('dashboard.history_query_indicator.token_detection_status.detecting_with_details', {
        current: currentStep,
        total,
      });

      currentOperationData = {
        address: runningItem.address,
        chain: runningItem.chain,
        status: t('dashboard.history_query_indicator.token_detection_status.detecting'),
        type: TaskType.FETCH_DETECTED_TOKENS,
      };
    }
    else if (!isTokenDetection) {
      const chainName = get(getChainName(runningItem.chain));

      if (total > 1) {
        currentOperation = t('dashboard.history_query_indicator.balance_status.querying_chain_balances_with_progress', {
          chain: chainName,
          current: currentStep,
          total,
        });
      }
      else {
        currentOperation = t('dashboard.history_query_indicator.balance_status.querying_chain_balances', {
          chain: chainName,
        });
      }

      currentOperationData = {
        chain: runningItem.chain,
        status: t('dashboard.history_query_indicator.balance_status.querying_chain_balances', { chain: chainName }),
        type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      };
    }
    else {
      currentOperation = t('dashboard.history_query_indicator.token_detection_status.detecting');
      currentOperationData = {
        status: t('dashboard.history_query_indicator.token_detection_status.detecting'),
        type: TaskType.FETCH_DETECTED_TOKENS,
      };
    }

    return {
      currentOperation,
      currentOperationData,
      currentStep,
      percentage: get(progress),
      totalSteps: total,
      type: runningItem.type,
    };
  });

  return {
    balanceProgress,
    isBalanceQuerying,
  };
}
