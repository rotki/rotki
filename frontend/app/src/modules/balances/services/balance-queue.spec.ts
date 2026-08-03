import { flushPromises } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { BalanceQueueService, type QueueItem, type QueueItemMetadata } from '@/modules/balances/services/balance-queue';
import { TaskType } from '@/modules/core/tasks/task-type';

interface TestMetadata extends QueueItemMetadata {
  chain: string;
  address?: string;
}

interface Gate {
  promise: Promise<void>;
  open: () => void;
}

/**
 * A manually released execution, used instead of sleeping inside `executeFn`.
 * The queue only ever suspends at `await item.executeFn()`, so holding that
 * await open gives the test exact control over how long an item stays running.
 */
function createGate(): Gate {
  let open!: () => void;
  const promise = new Promise<void>((resolve) => {
    open = resolve;
  });
  return { open, promise };
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
      const gates: Gate[] = [];
      const createExecuteFn = (id: string): (() => Promise<void>) => {
        const gate = createGate();
        gates.push(gate);
        return vi.fn(async () => {
          executionOrder.push(`start-${id}`);
          await gate.promise;
          executionOrder.push(`end-${id}`);
        });
      };

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

      // enqueue runs the items synchronously up to their first await, so the
      // concurrency window is already open here — no need to sample it later.
      expect(queue.getStats()).toMatchObject({ pending: 1, running: 2 });
      expect(executionOrder).toEqual(['start-1', 'start-2']);

      // Wait for all to complete
      for (const gate of gates)
        gate.open();
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
      const gates = new Array(5).fill(null).map(() => createGate());
      const executeFns = gates.map(gate =>
        vi.fn(async () => {
          await gate.promise;
        }),
      );

      const items: QueueItem<TestMetadata>[] = executeFns.map((fn, i) => ({
        executeFn: fn,
        id: `test-${i}`,
        metadata: { chain: 'eth' },
        type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      }));

      const batchPromise = queue.enqueueBatch(items);

      // Two items are already running and the rest are pending at this point
      expect(queue.getStats()).toMatchObject({
        pending: 3,
        running: 2,
      });

      queue.clear();

      await expect(batchPromise).resolves.toBeUndefined();

      expect(queue.getStats()).toMatchObject({
        pending: 0,
        running: 0,
      });

      // Release the two in-flight executions so nothing dangles past the test
      for (const gate of gates)
        gate.open();
      await flushPromises();
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

      const gate = createGate();
      const item: QueueItem<TestMetadata> = {
        executeFn: async () => gate.promise,
        id: 'test-1',
        metadata: { chain: 'eth' },
        type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      };

      const enqueuePromise = queue.enqueue(item);

      // The item is already running: enqueue does not yield before executeFn
      expect(queue.isProcessing()).toBe(true);

      // Release the gate to complete the item
      gate.open();

      // The item is removed from runningItems before its promise resolves,
      // so awaiting it is enough — no cleanup delay needed.
      await enqueuePromise;

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

  describe('canProcess callback', () => {
    it('should block processing when canProcess returns false', async () => {
      let canProcess = false;
      queue.setCanProcess(() => canProcess);

      const executeFn = vi.fn().mockResolvedValue(undefined);
      const item: QueueItem<TestMetadata> = {
        executeFn,
        id: 'test-1',
        metadata: { chain: 'eth' },
        type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      };

      // Enqueue without awaiting since it will be blocked
      const enqueuePromise = queue.enqueue(item);

      // The canProcess check happens synchronously inside enqueue, so the
      // blocked state is observable immediately.
      // Item should be pending, not executed
      expect(executeFn).not.toHaveBeenCalled();
      expect(queue.getStats()).toMatchObject({
        completed: 0,
        pending: 1,
        running: 0,
      });

      // Now allow processing
      canProcess = true;
      queue.retryProcessing();

      await enqueuePromise;

      expect(executeFn).toHaveBeenCalledTimes(1);
      expect(queue.getStats()).toMatchObject({
        completed: 1,
        pending: 0,
        running: 0,
      });
    });

    it('should process immediately when canProcess returns true', async () => {
      queue.setCanProcess(() => true);

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
        pending: 0,
        running: 0,
      });
    });

    it('should not retry if not waiting for canProcess', () => {
      const executeFn = vi.fn().mockResolvedValue(undefined);

      // No items in queue, retryProcessing should be a no-op
      queue.retryProcessing();

      expect(executeFn).not.toHaveBeenCalled();
    });

    it('should handle canProcess callback returning reactive value', async () => {
      // Simulate a reactive ref that changes value
      let isDecoding = true;
      queue.setCanProcess(() => !isDecoding);

      const executeFn = vi.fn().mockResolvedValue(undefined);
      const item: QueueItem<TestMetadata> = {
        executeFn,
        id: 'test-1',
        metadata: { chain: 'eth' },
        type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      };

      // Enqueue while "decoding" is true (canProcess returns false)
      const enqueuePromise = queue.enqueue(item);

      expect(executeFn).not.toHaveBeenCalled();

      // Simulate decoding finished
      isDecoding = false;
      queue.retryProcessing();

      await enqueuePromise;

      expect(executeFn).toHaveBeenCalledTimes(1);
    });

    it('should block mid-batch when canProcess becomes false', async () => {
      let canProcess = true;
      queue.setCanProcess(() => canProcess);

      const executionOrder: string[] = [];
      const gates = new Map<string, Gate>();
      const createSlowExecuteFn = (id: string): (() => Promise<void>) => {
        const gate = createGate();
        gates.set(id, gate);
        return vi.fn(async () => {
          executionOrder.push(`start-${id}`);
          await gate.promise;
          executionOrder.push(`end-${id}`);
        });
      };

      const items: QueueItem<TestMetadata>[] = [
        {
          executeFn: createSlowExecuteFn('1'),
          id: 'test-1',
          metadata: { chain: 'eth' },
          type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
        },
        {
          executeFn: createSlowExecuteFn('2'),
          id: 'test-2',
          metadata: { chain: 'btc' },
          type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
        },
        {
          executeFn: createSlowExecuteFn('3'),
          id: 'test-3',
          metadata: { chain: 'dot' },
          type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
        },
      ];

      const batchPromise = queue.enqueueBatch(items);

      // The first two items start immediately (concurrency is 2), the third waits
      expect(queue.getStats()).toMatchObject({ pending: 1, running: 2 });

      // Block, then let the first item finish: the slot it frees must not be
      // filled while canProcess is false.
      canProcess = false;
      gates.get('1')!.open();
      await flushPromises();

      expect(queue.getStats()).toMatchObject({ completed: 1, pending: 1, running: 1 });
      expect(executionOrder).not.toContain('start-3');

      // Unblock and complete
      canProcess = true;
      queue.retryProcessing();

      expect(queue.getStats()).toMatchObject({ pending: 0, running: 2 });

      gates.get('2')!.open();
      gates.get('3')!.open();

      await batchPromise;

      expect(queue.getStats().completed).toBe(3);
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

    it('should have clean state on new instance after reset', async () => {
      const instance1 = BalanceQueueService.getInstance<TestMetadata>();
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

      // Process items including a failure to populate completedItems and failedItems
      const items: QueueItem<TestMetadata>[] = [
        {
          executeFn: vi.fn().mockResolvedValue(undefined),
          id: 'test-1',
          metadata: { chain: 'eth' },
          type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
        },
        {
          executeFn: vi.fn().mockRejectedValue(new Error('fail')),
          id: 'test-2',
          metadata: { chain: 'btc' },
          type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
        },
      ];

      await instance1.enqueueBatch(items);
      expect(instance1.getStats().completed).toBe(1);
      expect(instance1.getStats().failed).toBe(1);

      BalanceQueueService.resetInstance();
      const instance2 = BalanceQueueService.getInstance<TestMetadata>();

      // New instance should have completely clean state
      expect(instance2.getStats()).toEqual({
        completed: 0,
        failed: 0,
        pending: 0,
        running: 0,
        total: 0,
      });
      expect(instance2.getAllItems()).toHaveLength(0);

      consoleError.mockRestore();
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
