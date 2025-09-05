import type { ComputedRef, Ref } from 'vue';
import type {
  BalanceQueryQueueItem,
} from '@/modules/dashboard/progress/types';
import { get, set, watchDebounced } from '@vueuse/shared';
import { BalanceQueueService, type QueueItem, type QueueItemMetadata, type QueueStats } from '@/services/balance-queue';
import { TaskType } from '@/types/task-type';

interface BalanceQueueMetadata extends QueueItemMetadata {
  chain: string;
  address?: string;
}

interface UseBalanceQueueReturn {
  queueTokenDetection: (
    chain: string,
    addresses: string[],
    fetchFn: (address: string) => Promise<void>
  ) => Promise<void>;
  queueBalanceQueries: (
    chains: string[],
    fetchFn: (chain: string) => Promise<void>
  ) => Promise<void>;
  queueMixedOperations: (operations: {
    tokenDetection?: Array<{
      chain: string;
      addresses: string[];
      fn: (address: string) => Promise<void>;
    }>;
    balanceQueries?: {
      chains: string[];
      fn: (chain: string) => Promise<void>;
    };
  }) => Promise<void>;
  clearQueue: () => void;
  progress: Readonly<ComputedRef<number>>;
  isProcessing: Readonly<ComputedRef<boolean>>;
  stats: Readonly<Ref<QueueStats>>;
  queueItems: Readonly<ComputedRef<BalanceQueryQueueItem[]>>;
  totalItems: Readonly<ComputedRef<number>>;
  completedItems: Readonly<ComputedRef<number>>;
  pendingItems: Readonly<ComputedRef<number>>;
  runningItems: Readonly<ComputedRef<number>>;
}

// Shared state across all composable instances
const sharedStats = ref<QueueStats>({
  completed: 0,
  failed: 0,
  pending: 0,
  running: 0,
  total: 0,
});

const sharedItems = ref<Map<string, BalanceQueryQueueItem>>(new Map());

// Singleton balance queue instance
let balanceQueue: BalanceQueueService<BalanceQueueMetadata> | null = null;
let pollInterval: NodeJS.Timeout | null = null;

function getBalanceQueue(): BalanceQueueService<BalanceQueueMetadata> {
  if (!balanceQueue) {
    balanceQueue = BalanceQueueService.getInstance<BalanceQueueMetadata>(2);

    // Set up progress callback to update shared state
    balanceQueue.setOnProgress(() => {
      updateSharedState();
    });
  }
  return balanceQueue;
}

function updateSharedState(): void {
  const queue = getBalanceQueue();
  set(sharedStats, queue.getStats());

  const allItems = queue.getAllItems();
  const itemsMap = new Map<string, BalanceQueryQueueItem>();

  for (const item of allItems) {
    const status = item.status === 'failed' ? 'completed' : (item.status || 'pending');
    const queueItem: BalanceQueryQueueItem = {
      addedAt: item.addedAt || Date.now(),
      chain: item.metadata.chain,
      id: item.id,
      status,
      type: item.type,
      ...(item.metadata.address && { address: item.metadata.address }),
    };
    itemsMap.set(item.id, queueItem);
  }

  set(sharedItems, itemsMap);
}

function stopPolling(): void {
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
}

function startPolling(): void {
  if (pollInterval)
    return;

  updateSharedState();

  pollInterval = setInterval(() => {
    updateSharedState();

    const queue = getBalanceQueue();
    if (!queue.isProcessing()) {
      stopPolling();
    }
  }, 100);
}

export function useBalanceQueue(): UseBalanceQueueReturn {
  const queue = getBalanceQueue();

  const queueItems = computed<BalanceQueryQueueItem[]>(() => Array.from(get(sharedItems).values()));

  const totalItems = computed<number>(() => get(sharedStats).total);

  const completedItems = computed<number>(() => get(sharedStats).completed);

  const pendingItems = computed<number>(() => get(sharedStats).pending);

  const runningItems = computed<number>(() => get(sharedStats).running);

  const progress = computed<number>(() => {
    const stats = get(sharedStats);
    if (stats.total === 0)
      return 0;

    return Math.round(((stats.completed + stats.failed) / stats.total) * 100);
  });

  const isProcessing = computed<boolean>(() => {
    const stats = get(sharedStats);
    return stats.running > 0 || stats.pending > 0;
  });

  const queueTokenDetection = async (
    chain: string,
    addresses: string[],
    fetchFn: (address: string) => Promise<void>,
  ): Promise<void> => {
    if (addresses.length === 0)
      return;

    startPolling();

    const items: QueueItem<BalanceQueueMetadata>[] = addresses.map(address => ({
      executeFn: async () => fetchFn(address),
      id: `token-${chain}-${address}`,
      metadata: { address, chain },
      type: TaskType.FETCH_DETECTED_TOKENS,
    }));

    await queue.enqueueBatch(items);
  };

  const queueBalanceQueries = async (
    chains: string[],
    fetchFn: (chain: string) => Promise<void>,
  ): Promise<void> => {
    if (chains.length === 0)
      return;

    startPolling();

    const items: QueueItem<BalanceQueueMetadata>[] = chains.map(chain => ({
      executeFn: async () => fetchFn(chain),
      id: `balance-${chain}`,
      metadata: { chain },
      type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
    }));

    await queue.enqueueBatch(items);
  };

  const queueMixedOperations = async (operations: {
    tokenDetection?: Array<{
      chain: string;
      addresses: string[];
      fn: (address: string) => Promise<void>;
    }>;
    balanceQueries?: {
      chains: string[];
      fn: (chain: string) => Promise<void>;
    };
  }): Promise<void> => {
    if (operations.tokenDetection) {
      for (const { addresses, chain, fn } of operations.tokenDetection) {
        await queueTokenDetection(chain, addresses, fn);
      }
    }

    if (operations.balanceQueries) {
      await queueBalanceQueries(operations.balanceQueries.chains, operations.balanceQueries.fn);
    }
  };

  const clearQueue = (): void => {
    queue.clear();
    set(sharedItems, new Map());
    updateSharedState();
  };

  watchDebounced(
    isProcessing,
    (processing) => {
      if (!processing && get(completedItems) === get(totalItems) && get(totalItems) > 0) {
        setTimeout(() => {
          if (!get(isProcessing)) {
            queue.clearCompleted();
            clearQueue();
          }
        }, 1000);
      }
    },
    { debounce: 500 },
  );

  onUnmounted(() => {
    // Note: We don't stop polling here since it's shared across all instances
    // The polling will stop automatically when no items are processing
  });

  return {
    clearQueue,
    completedItems,
    isProcessing,
    pendingItems,
    progress,
    queueBalanceQueries,
    queueItems,
    queueMixedOperations,
    queueTokenDetection,
    runningItems,
    stats: readonly(sharedStats),
    totalItems,
  };
}
