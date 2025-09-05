import { beforeEach, describe, expect, it, vi } from 'vitest';
import { BalanceQueueService, type QueueItem, type QueueItemMetadata } from '@/services/balance-queue';
import { TaskType } from '@/types/task-type';

interface TestMetadata extends QueueItemMetadata {
  chain: string;
  address?: string;
}

describe('balanceQueueService', () => {
  let queue: BalanceQueueService<TestMetadata>;

  beforeEach(() => {
    BalanceQueueService.resetInstance();
    queue = new BalanceQueueService<TestMetadata>(2);
  });

  describe('basic operations', () => {
    it('should enqueue and process a single item', async () => {
      const executeFn = vi.fn().mockResolvedValue(undefined);

      const item: QueueItem<TestMetadata> = {
        executeFn,
        id: 'test-1',
        metadata: { chain: 'eth' },
        type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      };

      await queue.enqueue(item);

      expect(executeFn).toHaveBeenCalledTimes(1);
      expect(queue.getStats()).toMatchObject({
        completed: 1,
        failed: 0,
        pending: 0,
        running: 0,
        total: 1,
      });
    });

    it('should handle failed items', async () => {
      const error = new Error('Test error');
      const executeFn = vi.fn().mockRejectedValue(error);
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

      const item: QueueItem<TestMetadata> = {
        executeFn,
        id: 'test-fail',
        metadata: { chain: 'eth' },
        type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      };

      await queue.enqueue(item);

      expect(executeFn).toHaveBeenCalledTimes(1);
      expect(consoleError).toHaveBeenCalledWith('Queue item test-fail failed:', error);
      expect(queue.getStats()).toMatchObject({
        completed: 0,
        failed: 1,
        pending: 0,
        running: 0,
        total: 1,
      });

      consoleError.mockRestore();
    });

    it('should respect max concurrency', async () => {
      const executionOrder: string[] = [];
      const createExecuteFn = (id: string): (() => Promise<void>) => vi.fn(async () => {
        executionOrder.push(`start-${id}`);
        await new Promise(resolve => setTimeout(resolve, 50));
        executionOrder.push(`end-${id}`);
      });

      const items: QueueItem<TestMetadata>[] = [
        {
          executeFn: createExecuteFn('1'),
          id: 'test-1',
          metadata: { chain: 'eth' },
          type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
        },
        {
          executeFn: createExecuteFn('2'),
          id: 'test-2',
          metadata: { chain: 'btc' },
          type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
        },
        {
          executeFn: createExecuteFn('3'),
          id: 'test-3',
          metadata: { chain: 'dot' },
          type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
        },
      ];

      // Start enqueueing items
      const promises = items.map(async item => queue.enqueue(item));

      // Wait a bit to check concurrency
      await new Promise(resolve => setTimeout(resolve, 10));
      expect(queue.getStats().running).toBeLessThanOrEqual(2);

      // Wait for all to complete
      await Promise.all(promises);

      expect(executionOrder).toHaveLength(6);
      expect(executionOrder.slice(0, 2)).toEqual(['start-1', 'start-2']);
    });
  });

  describe('batch operations', () => {
    it('should process batch of items', async () => {
      const executeFns = [
        vi.fn().mockResolvedValue(undefined),
        vi.fn().mockResolvedValue(undefined),
        vi.fn().mockResolvedValue(undefined),
      ];

      const items: QueueItem<TestMetadata>[] = executeFns.map((fn, i) => ({
        executeFn: fn,
        id: `test-${i}`,
        metadata: { chain: 'eth' },
        type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      }));

      await queue.enqueueBatch(items);

      for (const fn of executeFns) {
        expect(fn).toHaveBeenCalledTimes(1);
      }

      expect(queue.getStats()).toMatchObject({
        completed: 3,
        failed: 0,
        pending: 0,
        running: 0,
        total: 3,
      });
    });

    it('should resolve batch promise even with failures', async () => {
      const executeFns = [
        vi.fn().mockResolvedValue(undefined),
        vi.fn().mockRejectedValue(new Error('Test error')),
        vi.fn().mockResolvedValue(undefined),
      ];
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

      const items: QueueItem<TestMetadata>[] = executeFns.map((fn, i) => ({
        executeFn: fn,
        id: `test-${i}`,
        metadata: { chain: 'eth' },
        type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      }));

      await queue.enqueueBatch(items);

      expect(queue.getStats()).toMatchObject({
        completed: 2,
        failed: 1,
        pending: 0,
        running: 0,
        total: 3,
      });

      consoleError.mockRestore();
    });

    it('should handle empty batch', async () => {
      await expect(queue.enqueueBatch([])).resolves.toBeUndefined();

      expect(queue.getStats()).toMatchObject({
        completed: 0,
        failed: 0,
        pending: 0,
        running: 0,
        total: 0,
      });
    });
  });

  describe('queue management', () => {
    it('should clear queue', async () => {
      const executeFns = new Array(5).fill(null).map(() =>
        vi.fn(async () => {
          await new Promise(resolve => setTimeout(resolve, 100));
        }),
      );

      const items: QueueItem<TestMetadata>[] = executeFns.map((fn, i) => ({
        executeFn: fn,
        id: `test-${i}`,
        metadata: { chain: 'eth' },
        type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      }));

      const batchPromise = queue.enqueueBatch(items);

      await new Promise(resolve => setTimeout(resolve, 10));

      queue.clear();

      await expect(batchPromise).rejects.toThrow('Queue cleared');

      expect(queue.getStats()).toMatchObject({
        pending: 0,
        running: 0,
      });
    });

    it('should clear completed items', async () => {
      const items: QueueItem<TestMetadata>[] = [
        {
          executeFn: vi.fn().mockResolvedValue(undefined),
          id: 'test-1',
          metadata: { chain: 'eth' },
          type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
        },
        {
          executeFn: vi.fn().mockRejectedValue(new Error('Test')),
          id: 'test-2',
          metadata: { chain: 'btc' },
          type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
        },
      ];
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

      await queue.enqueueBatch(items);

      expect(queue.getStats().total).toBe(2);

      queue.clearCompleted();

      expect(queue.getStats()).toMatchObject({
        completed: 0,
        failed: 0,
        pending: 0,
        running: 0,
        total: 0,
      });

      consoleError.mockRestore();
    });
  });

  describe('progress tracking', () => {
    it('should calculate progress correctly', async () => {
      expect(queue.getProgress()).toBe(0);

      const items: QueueItem<TestMetadata>[] = new Array(4).fill(null).map((_, i) => ({
        executeFn: vi.fn().mockResolvedValue(undefined),
        id: `test-${i}`,
        metadata: { chain: 'eth' },
        type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      }));

      await queue.enqueueBatch(items);

      expect(queue.getProgress()).toBe(100);
    });

    it('should track processing state', async () => {
      expect(queue.isProcessing()).toBe(false);

      let resolveWait: (() => void) | null = null;
      const waitPromise = new Promise<void>((resolve) => {
        resolveWait = resolve;
      });
      const item: QueueItem<TestMetadata> = {
        executeFn: async () => waitPromise,
        id: 'test-1',
        metadata: { chain: 'eth' },
        type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      };

      const enqueuePromise = queue.enqueue(item);

      // Wait a bit to ensure the item is running
      await new Promise(resolve => setTimeout(resolve, 10));
      expect(queue.isProcessing()).toBe(true);

      // Resolve the wait promise to complete the item
      resolveWait!();

      // Wait for the item to complete
      await enqueuePromise;

      // Small delay to ensure cleanup
      await new Promise(resolve => setTimeout(resolve, 10));
      expect(queue.isProcessing()).toBe(false);
    });
  });

  describe('callbacks', () => {
    it('should call onCompletion callback', async () => {
      const onCompletion = vi.fn();
      queue.setOnCompletion(onCompletion);

      const item: QueueItem<TestMetadata> = {
        executeFn: vi.fn().mockResolvedValue(undefined),
        id: 'test-1',
        metadata: { chain: 'eth' },
        type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      };

      await queue.enqueue(item);

      expect(onCompletion).toHaveBeenCalledTimes(1);
    });

    it('should call onProgress callback', async () => {
      const onProgress = vi.fn();
      queue.setOnProgress(onProgress);

      const item: QueueItem<TestMetadata> = {
        executeFn: vi.fn().mockResolvedValue(undefined),
        id: 'test-1',
        metadata: { chain: 'eth' },
        type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      };

      await queue.enqueue(item);

      expect(onProgress).toHaveBeenCalled();
      expect(onProgress).toHaveBeenCalledWith(expect.objectContaining({
        completed: expect.any(Number),
        failed: expect.any(Number),
        pending: expect.any(Number),
        running: expect.any(Number),
        total: expect.any(Number),
      }));
    });
  });

  describe('getItems', () => {
    it('should return categorized items', async () => {
      const items: QueueItem<TestMetadata>[] = [
        {
          executeFn: vi.fn().mockResolvedValue(undefined),
          id: 'success-1',
          metadata: { chain: 'eth' },
          type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
        },
        {
          executeFn: vi.fn().mockRejectedValue(new Error('Test')),
          id: 'fail-1',
          metadata: { chain: 'btc' },
          type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
        },
      ];
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

      await queue.enqueueBatch(items);

      const categorized = queue.getItems();

      expect(categorized.completed).toHaveLength(1);
      expect(categorized.failed).toHaveLength(1);
      expect(categorized.pending).toHaveLength(0);
      expect(categorized.running).toHaveLength(0);

      expect(categorized.completed[0].id).toBe('success-1');
      expect(categorized.failed[0].id).toBe('fail-1');

      consoleError.mockRestore();
    });

    it('should return all items', async () => {
      const items: QueueItem<TestMetadata>[] = new Array(3).fill(null).map((_, i) => ({
        executeFn: vi.fn().mockResolvedValue(undefined),
        id: `test-${i}`,
        metadata: { chain: 'eth' },
        type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      }));

      await queue.enqueueBatch(items);

      const allItems = queue.getAllItems();

      expect(allItems).toHaveLength(3);
      expect(allItems.map(item => item.id).sort()).toEqual(['test-0', 'test-1', 'test-2']);
    });
  });

  describe('singleton pattern', () => {
    it('should return same instance', () => {
      const instance1 = BalanceQueueService.getInstance<TestMetadata>();
      const instance2 = BalanceQueueService.getInstance<TestMetadata>();

      expect(instance1).toBe(instance2);
    });

    it('should reset instance', () => {
      const instance1 = BalanceQueueService.getInstance<TestMetadata>();
      BalanceQueueService.resetInstance();
      const instance2 = BalanceQueueService.getInstance<TestMetadata>();

      expect(instance1).not.toBe(instance2);
    });
  });

  describe('token detection scenario', () => {
    it('should handle token detection workflow', async () => {
      const addresses = ['0x123', '0x456', '0x789'];
      const chain = 'ethereum';
      const executeFns = addresses.map(() => vi.fn().mockResolvedValue(undefined));

      const items: QueueItem<TestMetadata>[] = addresses.map((address, i) => ({
        executeFn: executeFns[i],
        id: `token-${chain}-${address}`,
        metadata: { address, chain },
        type: TaskType.FETCH_DETECTED_TOKENS,
      }));

      await queue.enqueueBatch(items);

      for (const fn of executeFns) {
        expect(fn).toHaveBeenCalledTimes(1);
      }

      const allItems = queue.getAllItems();
      expect(allItems).toHaveLength(3);
      for (const item of allItems) {
        expect(item.type).toBe(TaskType.FETCH_DETECTED_TOKENS);
        expect(item.metadata.chain).toBe(chain);
        expect(addresses).toContain(item.metadata.address);
      }
    });
  });

  describe('balance query scenario', () => {
    it('should handle balance query workflow', async () => {
      const chains = ['ethereum', 'bitcoin', 'polkadot'];
      const executeFns = chains.map(() => vi.fn().mockResolvedValue(undefined));

      const items: QueueItem<TestMetadata>[] = chains.map((chain, i) => ({
        executeFn: executeFns[i],
        id: `balance-${chain}`,
        metadata: { chain },
        type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      }));

      await queue.enqueueBatch(items);

      for (const fn of executeFns) {
        expect(fn).toHaveBeenCalledTimes(1);
      }

      const allItems = queue.getAllItems();
      expect(allItems).toHaveLength(3);
      for (const item of allItems) {
        expect(item.type).toBe(TaskType.QUERY_BLOCKCHAIN_BALANCES);
        expect(chains).toContain(item.metadata.chain);
      }
    });
  });
});
