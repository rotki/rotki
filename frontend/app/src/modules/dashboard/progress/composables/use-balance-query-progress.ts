import type { ComputedRef } from 'vue';
import type {
  BalanceQueryProgressType,
  BalanceQueryQueueItem,
  CommonQueryProgressData,
} from '@/modules/dashboard/progress/types';
import { get } from '@vueuse/shared';
import { useBalanceQueue } from '@/composables/balances/use-balance-queue';
import { useSupportedChains } from '@/composables/info/chains';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

interface BalanceQueryProgressOperationData {
  type: BalanceQueryProgressType;
  chain?: string;
  address?: string;
  status: string;
}

export interface BalanceQueryProgress extends CommonQueryProgressData<BalanceQueryProgressOperationData> {}

interface UseBalanceQueryProgressReturn {
  balanceProgress: ComputedRef<BalanceQueryProgress | undefined>;
  isBalanceQuerying: ComputedRef<boolean>;
}

function createPendingItemProgress(
  item: BalanceQueryQueueItem,
  completed: number,
  total: number,
  progress: number,
  t: ReturnType<typeof useI18n>['t'],
): BalanceQueryProgress {
  const isTokenDetection = item.type === TaskType.FETCH_DETECTED_TOKENS;
  return {
    currentOperation: isTokenDetection
      ? t('dashboard.history_query_indicator.token_detection_status.detecting')
      : t('dashboard.history_query_indicator.balance_status.querying_balances'),
    currentOperationData: {
      address: item.address,
      chain: item.chain,
      status: 'pending',
      type: item.type,
    },
    currentStep: completed,
    percentage: progress,
    totalSteps: total,
  };
}

function createTokenDetectionProgress(
  item: BalanceQueryQueueItem,
  currentStep: number,
  total: number,
  progress: number,
  t: ReturnType<typeof useI18n>['t'],
): BalanceQueryProgress {
  const currentOperation = item.address
    ? t('dashboard.history_query_indicator.token_detection_status.detecting_with_details', {
        current: currentStep,
        total,
      })
    : t('dashboard.history_query_indicator.token_detection_status.detecting');

  return {
    currentOperation,
    currentOperationData: {
      address: item.address,
      chain: item.chain,
      status: t('dashboard.history_query_indicator.token_detection_status.detecting'),
      type: TaskType.FETCH_DETECTED_TOKENS,
    },
    currentStep,
    percentage: progress,
    totalSteps: total,
  };
}

function createBalanceQueryProgress(
  item: BalanceQueryQueueItem,
  currentStep: number,
  total: number,
  progress: number,
  chainName: string,
  t: ReturnType<typeof useI18n>['t'],
): BalanceQueryProgress {
  const currentOperation = total > 1
    ? t('dashboard.history_query_indicator.balance_status.querying_chain_balances_with_progress', {
        chain: chainName,
        current: currentStep,
        total,
      })
    : t('dashboard.history_query_indicator.balance_status.querying_chain_balances', {
        chain: chainName,
      });

  return {
    currentOperation,
    currentOperationData: {
      chain: item.chain,
      status: t('dashboard.history_query_indicator.balance_status.querying_chain_balances', { chain: chainName }),
      type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
    },
    currentStep,
    percentage: progress,
    totalSteps: total,
  };
}

function createRunningItemProgress(
  item: BalanceQueryQueueItem,
  completed: number,
  total: number,
  progress: number,
  getChainName: ReturnType<typeof useSupportedChains>['getChainName'],
  t: ReturnType<typeof useI18n>['t'],
): BalanceQueryProgress {
  const currentStep = completed + 1;
  const isTokenDetection = item.type === TaskType.FETCH_DETECTED_TOKENS;

  if (isTokenDetection) {
    return createTokenDetectionProgress(item, currentStep, total, progress, t);
  }

  const chainName = get(getChainName(item.chain));
  return createBalanceQueryProgress(item, currentStep, total, progress, chainName, t);
}

export function useBalanceQueryProgress(): UseBalanceQueryProgressReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { getChainName } = useSupportedChains();
  const { useIsTaskRunning } = useTaskStore();
  const {
    completedItems,
    progress,
    queueItems,
    runningItems,
    totalItems,
  } = useBalanceQueue();

  const isBalanceQuerying = logicOr(
    useIsTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES),
    useIsTaskRunning(TaskType.FETCH_DETECTED_TOKENS),
    computed<boolean>(() => get(runningItems) > 0),
  );

  const balanceProgress = computed<BalanceQueryProgress | undefined>(() => {
    const items = get(queueItems);
    const total = get(totalItems);
    const completed = get(completedItems);
    const progressValue = get(progress);

    if (total === 0) {
      return undefined;
    }

    // Find current running item
    const runningItem = items.find(item => item.status === 'running');
    if (runningItem) {
      return createRunningItemProgress(runningItem, completed, total, progressValue, getChainName, t);
    }

    // Check for pending items
    const firstPending = items.find(item => item.status === 'pending');
    if (firstPending) {
      return createPendingItemProgress(firstPending, completed, total, progressValue, t);
    }

    return undefined;
  });

  return {
    balanceProgress,
    isBalanceQuerying,
  };
}
