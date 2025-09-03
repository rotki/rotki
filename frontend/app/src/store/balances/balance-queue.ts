import { TaskType } from '@/types/task-type';
import { LimitedParallelizationQueue } from '@/utils/limited-parallelization-queue';

interface QueueItem {
  id: string;
  type: TaskType.FETCH_DETECTED_TOKENS | TaskType.QUERY_BLOCKCHAIN_BALANCES;
  chain: string;
  address?: string;
  status: 'pending' | 'running' | 'completed';
  addedAt: number;
}

export const useBalanceQueueStore = defineStore('balances/queue', () => {
  // Create queue instance inside the store
  const queue = new LimitedParallelizationQueue(2);

  // Track all items in the queue
  const items = ref<Map<string, QueueItem>>(new Map());

  // Track operation batches
  const currentBatch = ref<string>();

  // Track pending promises for batch operations
  const batchPromises = new Map<string, { resolve: () => void; totalItems: number; completedItems: number }>();

  const queueItems = computed<QueueItem[]>(() => Array.from(get(items).values()));

  const totalItems = computed<number>(() => get(items).size);

  const completedItems = computed<number>(() =>
    get(queueItems).filter(item => item.status === 'completed').length,
  );

  const pendingItems = computed<number>(() =>
    get(queueItems).filter(item => item.status === 'pending').length,
  );

  const runningItems = computed<number>(() =>
    get(queueItems).filter(item => item.status === 'running').length,
  );

  const progress = computed<number>(() => {
    const total = get(totalItems);
    const completed = get(completedItems);
    return total > 0 ? Math.round((completed / total) * 100) : 0;
  });

  const isProcessing = computed<boolean>(() =>
    get(runningItems) > 0 || get(pendingItems) > 0,
  );

  const addToQueue = (item: Omit<QueueItem, 'status' | 'addedAt'>, fn: () => Promise<void>, batchId?: string): void => {
    const queueItem: QueueItem = {
      ...item,
      addedAt: Date.now(),
      status: 'pending',
    };

    // Add to tracking
    const currentItems = new Map(get(items));
    currentItems.set(item.id, queueItem);
    set(items, currentItems);

    // Queue the actual work
    queue.queue(item.id, async () => {
      // Mark as running
      const runningItems = new Map(get(items));
      const runningItem = runningItems.get(item.id);
      if (runningItem) {
        runningItem.status = 'running';
        set(items, runningItems);
      }

      try {
        // Execute the actual work
        await fn();

        // Mark as completed
        const completedItems = new Map(get(items));
        const completedItem = completedItems.get(item.id);
        if (completedItem) {
          completedItem.status = 'completed';
          set(items, completedItems);
        }

        // Check if this completes a batch
        if (batchId && batchPromises.has(batchId)) {
          const batch = batchPromises.get(batchId)!;
          batch.completedItems++;
          if (batch.completedItems >= batch.totalItems) {
            batch.resolve();
            batchPromises.delete(batchId);
          }
        }
      }
      catch (error) {
        // Still mark as completed even on error
        const errorItems = new Map(get(items));
        const errorItem = errorItems.get(item.id);
        if (errorItem) {
          errorItem.status = 'completed';
          set(items, errorItems);
        }

        // Check if this completes a batch (even on error)
        if (batchId && batchPromises.has(batchId)) {
          const batch = batchPromises.get(batchId)!;
          batch.completedItems++;
          if (batch.completedItems >= batch.totalItems) {
            batch.resolve();
            batchPromises.delete(batchId);
          }
        }

        throw error;
      }
    });
  };

  const clearQueue = (): void => {
    queue.clear();
    set(items, new Map());
    set(currentBatch, undefined);
    // Resolve any pending batch promises
    batchPromises.forEach(batch => batch.resolve());
    batchPromises.clear();
  };

  /**
   * Queue token detection operations
   */
  const queueTokenDetection = async (
    chain: string,
    addresses: string[],
    fn: (address: string) => Promise<void>,
  ): Promise<void> => {
    if (addresses.length === 0) {
      return Promise.resolve();
    }

    return new Promise((resolve) => {
      const batchId = `token-batch-${chain}-${Date.now()}`;

      // Register this batch
      batchPromises.set(batchId, {
        completedItems: 0,
        resolve,
        totalItems: addresses.length,
      });

      // Add all items to queue
      for (const address of addresses) {
        const id = `token-${chain}-${address}`;
        addToQueue(
          {
            address,
            chain,
            id,
            type: TaskType.FETCH_DETECTED_TOKENS,
          },
          async () => fn(address),
          batchId,
        );
      }
    });
  };

  /**
   * Queue balance query operations
   */
  const queueBalanceQueries = async (
    chains: string[],
    fn: (chain: string) => Promise<void>,
  ): Promise<void> => {
    if (chains.length === 0) {
      return Promise.resolve();
    }

    return new Promise((resolve) => {
      const batchId = `balance-batch-${Date.now()}`;

      // Register this batch
      batchPromises.set(batchId, {
        completedItems: 0,
        resolve,
        totalItems: chains.length,
      });

      // Add all chains to queue
      for (const chain of chains) {
        const id = `balance-${chain}`;
        addToQueue(
          {
            chain,
            id,
            type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
          },
          async () => fn(chain),
          batchId,
        );
      }
    });
  };

  /**
   * Queue mixed operations (for unified token detection + balance flow)
   */
  const queueMixedOperations = async (
    operations: {
      tokenDetection?: { chain: string; addresses: string[]; fn: (address: string) => Promise<void> }[];
      balanceQueries?: { chains: string[]; fn: (chain: string) => Promise<void> };
    },
  ): Promise<void> => {
    // Queue token detections first
    if (operations.tokenDetection) {
      for (const { addresses, chain, fn } of operations.tokenDetection) {
        await queueTokenDetection(chain, addresses, fn);
      }
    }

    // Then queue balance queries
    if (operations.balanceQueries) {
      await queueBalanceQueries(operations.balanceQueries.chains, operations.balanceQueries.fn);
    }
  };

  // Auto-clear completed operations after a delay
  watchDebounced(
    isProcessing,
    (processing) => {
      if (!processing && get(completedItems) === get(totalItems) && get(totalItems) > 0) {
        // All done, clear after a short delay
        setTimeout(() => {
          if (!get(isProcessing)) {
            clearQueue();
          }
        }, 1000);
      }
    },
    { debounce: 500 },
  );

  return {
    addToQueue,
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
    totalItems,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBalanceQueueStore, import.meta.hot));
