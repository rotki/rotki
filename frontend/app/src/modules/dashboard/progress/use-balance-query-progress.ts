import type { ComputedRef } from 'vue';
import type {
  BalanceQueryProgressType,
  BalanceQueryQueueItem,
  CommonQueryProgressData,
} from '@/modules/dashboard/progress/types';
import { get, set } from '@vueuse/shared';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { isTerminalStatus } from '@/modules/task-center/core/status';
import { type Activity, type ActivityId, ActivityKind, activityParts, ActivityStatus } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

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

const BALANCE_KINDS = new Set<ActivityKind>([ActivityKind.BLOCKCHAIN_BALANCES, ActivityKind.TOKEN_DETECTION]);

function createPendingItemProgress(
  item: BalanceQueryQueueItem,
  completed: number,
  total: number,
  progress: number,
  t: ReturnType<typeof useI18n>['t'],
): BalanceQueryProgress {
  const isTokenDetection = item.type === ActivityKind.TOKEN_DETECTION;
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
      type: ActivityKind.TOKEN_DETECTION,
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
      type: ActivityKind.BLOCKCHAIN_BALANCES,
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
  const isTokenDetection = item.type === ActivityKind.TOKEN_DETECTION;

  if (isTokenDetection) {
    return createTokenDetectionProgress(item, currentStep, total, progress, t);
  }

  const chainName = getChainName(item.chain);
  return createBalanceQueryProgress(item, currentStep, total, progress, chainName, t);
}

function statusLabel(status: ActivityStatus): BalanceQueryQueueItem['status'] {
  if (status === ActivityStatus.RUNNING)
    return 'running';
  if (status === ActivityStatus.PENDING)
    return 'pending';
  return 'completed';
}

function toQueueItem(activity: Activity): BalanceQueryQueueItem {
  const parts = activityParts(activity.id);
  const isDetection = activity.kind === ActivityKind.TOKEN_DETECTION;
  const status = statusLabel(activity.status);
  return {
    addedAt: activity.startedAt ?? 0,
    chain: parts[0] ?? '',
    id: activity.id,
    status,
    type: isDetection ? ActivityKind.TOKEN_DETECTION : ActivityKind.BLOCKCHAIN_BALANCES,
    ...(isDetection && parts[1] ? { address: parts[1] } : {}),
  };
}

/**
 * Per-batch progress for blockchain-balance + token-detection activities, rebuilt from the
 * orchestrator snapshot (the old `BalanceQueueService` is gone). A "wave" is the set of activity
 * ids seen active since the orchestrator was last idle for these kinds; terminal members stay in
 * the wave (so `completed / total` is exact) until the wave drains, then it clears after a short
 * debounce — mirroring the queue's clear-after-drain.
 */
export const useBalanceQueryProgress = createSharedComposable((): UseBalanceQueryProgressReturn => {
  const { t } = useI18n({ useScope: 'global' });
  const { getChainName } = useSupportedChains();
  const { useIsActive } = useTaskCenter();
  const { activities } = useTaskOrchestrator();

  const balanceActivities = computed<Activity[]>(() =>
    get(activities).filter(activity => BALANCE_KINDS.has(activity.kind)),
  );

  const waveIds = ref<Set<ActivityId>>(new Set());
  let clearTimer: ReturnType<typeof setTimeout> | undefined;

  watch(balanceActivities, (items) => {
    const active = items.filter(activity => !isTerminalStatus(activity.status));

    if (active.length > 0) {
      if (clearTimer) {
        clearTimeout(clearTimer);
        clearTimer = undefined;
      }
      const next = new Set(get(waveIds));
      let changed = false;
      for (const activity of active) {
        if (!next.has(activity.id)) {
          next.add(activity.id);
          changed = true;
        }
      }
      if (changed)
        set(waveIds, next);
    }
    else if (get(waveIds).size > 0 && !clearTimer) {
      clearTimer = setTimeout(() => {
        set(waveIds, new Set());
        clearTimer = undefined;
      }, 1000);
    }
  }, { immediate: true });

  onScopeDispose(() => {
    if (clearTimer)
      clearTimeout(clearTimer);
  });

  const waveItems = computed<Activity[]>(() => {
    const ids = get(waveIds);
    return get(balanceActivities).filter(activity => ids.has(activity.id));
  });

  const totalItems = computed<number>(() => get(waveItems).length);
  const completedItems = computed<number>(() => get(waveItems).filter(activity => isTerminalStatus(activity.status)).length);
  const progress = computed<number>(() => {
    const total = get(totalItems);
    return total === 0 ? 0 : Math.round((get(completedItems) / total) * 100);
  });

  const isBalanceQuerying = logicOr(
    useIsActive(ActivityKind.BLOCKCHAIN_BALANCES),
    useIsActive(ActivityKind.TOKEN_DETECTION),
  );

  const balanceProgress = computed<BalanceQueryProgress | undefined>(() => {
    const items = get(waveItems);
    const total = get(totalItems);
    const completed = get(completedItems);
    const progressValue = get(progress);

    if (total === 0) {
      return undefined;
    }

    const runningItem = items.find(activity => activity.status === ActivityStatus.RUNNING);
    if (runningItem) {
      return createRunningItemProgress(toQueueItem(runningItem), completed, total, progressValue, getChainName, t);
    }

    const firstPending = items.find(activity => activity.status === ActivityStatus.PENDING);
    if (firstPending) {
      return createPendingItemProgress(toQueueItem(firstPending), completed, total, progressValue, t);
    }

    return undefined;
  });

  return {
    balanceProgress,
    isBalanceQuerying,
  };
});
