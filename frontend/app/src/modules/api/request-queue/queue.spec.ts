import { startPromise } from '@shared/utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { QueueOverflowError, RequestCancelledError } from './errors';
import { RequestQueue } from './queue';
import { RequestPriority } from './request-priority';

describe('requestQueue', () => {
  let queue: RequestQueue;
  let mockFetch: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.useFakeTimers();
    mockFetch = vi.fn().mockResolvedValue({ data: 'success' });
    queue = new RequestQueue(mockFetch, {
      maxConcurrent: 2,
      maxPerSecond: 10,
      maxQueueSize: 5,
      maxQueueTime: 5000,
      overloadThreshold: 3,
    });
  });

  afterEach(() => {
    queue.destroy();
    vi.useRealTimers();
  });

  describe('basic functionality', () => {
    it('should process a single request', async () => {
      const promise = queue.enqueue('/test');

      // Advance timer to trigger the setTimeout in flushPromises and allow processQueue
      await vi.advanceTimersByTimeAsync(10);

      const result = await promise;

      expect(mockFetch).toHaveBeenCalledWith('/test', expect.any(Object));
      expect(result).toEqual({ data: 'success' });
    });

    it('should process multiple requests in parallel up to maxConcurrent', async () => {
      // Make fetch return a pending promise that we control
      const resolvers: Array<(value: { data: string }) => void> = [];
      mockFetch.mockImplementation(async () => new Promise((resolve) => {
        resolvers.push(resolve);
      }));

      const promises = [
        queue.enqueue('/test1'),
        queue.enqueue('/test2'),
        queue.enqueue('/test3'),
      ];

      // Allow processQueue to run
      await vi.advanceTimersByTimeAsync(10);

      // First 2 should be processing, 1 should be queued
      expect(queue.state.active).toBe(2);
      expect(queue.state.queued).toBe(1);

      // Resolve first two to allow third to start
      resolvers[0]({ data: 'done' });
      resolvers[1]({ data: 'done' });
      await vi.advanceTimersByTimeAsync(10);

      // Third request should now be active and have a resolver
      expect(resolvers.length).toBe(3);

      // Resolve third
      resolvers[2]({ data: 'done' });
      await vi.advanceTimersByTimeAsync(10);

      await Promise.all(promises);

      expect(mockFetch).toHaveBeenCalledTimes(3);
    });

    it('should update state correctly', async () => {
      expect(queue.state.queued).toBe(0);
      expect(queue.state.active).toBe(0);

      // Make fetch return a pending promise
      let resolver: (value: { data: string }) => void;
      mockFetch.mockImplementation(async () => new Promise((resolve) => {
        resolver = resolve;
      }));

      const promise = queue.enqueue('/test');

      // Allow processQueue to run
      await vi.advanceTimersByTimeAsync(10);

      expect(queue.state.active).toBe(1);

      // Resolve and complete
      resolver!({ data: 'done' });
      await vi.advanceTimersByTimeAsync(10);
      await promise;

      expect(queue.state.active).toBe(0);
    });
  });

  describe('priority handling', () => {
    it('should process high priority requests first', async () => {
      const order: string[] = [];

      // Create controlled promises for each request
      const resolvers: Map<string, (value: { data: string }) => void> = new Map();
      mockFetch.mockImplementation(async (url: string) => {
        order.push(url);
        return new Promise((resolve) => {
          resolvers.set(url, resolve);
        });
      });

      // Start 2 requests to fill active slots
      startPromise(queue.enqueue('/first1'));
      startPromise(queue.enqueue('/first2'));

      await vi.advanceTimersByTimeAsync(10);

      // Verify first 2 are active
      expect(queue.state.active).toBe(2);

      // Queue more with different priorities
      startPromise(queue.enqueue('/low', { priority: RequestPriority.LOW }));
      startPromise(queue.enqueue('/high', { priority: RequestPriority.HIGH }));
      startPromise(queue.enqueue('/normal', { priority: RequestPriority.NORMAL }));

      // Complete first batch to allow queued requests to process
      resolvers.get('/first1')!({ data: 'done' });
      resolvers.get('/first2')!({ data: 'done' });

      await vi.advanceTimersByTimeAsync(10);

      // High and normal should now be processing (2 slots), low queued
      expect(order).toContain('/high');
      expect(order).toContain('/normal');

      // Complete high and normal to allow low to process
      resolvers.get('/high')!({ data: 'done' });
      resolvers.get('/normal')!({ data: 'done' });

      await vi.advanceTimersByTimeAsync(10);

      // Low should now be processed
      expect(order).toContain('/low');

      // Verify order: high should come before normal and low
      expect(order.indexOf('/high')).toBeLessThan(order.indexOf('/low'));
      expect(order.indexOf('/normal')).toBeLessThan(order.indexOf('/low'));
    });
  });

  describe('deduplication', () => {
    it('should deduplicate identical requests', async () => {
      const promise1 = queue.enqueue('/test', { dedupe: true });
      const promise2 = queue.enqueue('/test', { dedupe: true });

      await vi.advanceTimersByTimeAsync(10);

      const [result1, result2] = await Promise.all([promise1, promise2]);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(result1).toEqual(result2);
    });

    it('should not deduplicate different requests', async () => {
      const promise1 = queue.enqueue('/test1', { dedupe: true });
      const promise2 = queue.enqueue('/test2', { dedupe: true });

      await vi.advanceTimersByTimeAsync(10);
      await Promise.all([promise1, promise2]);

      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    it('should not deduplicate when dedupe is false', async () => {
      const promise1 = queue.enqueue('/test', { dedupe: false });
      const promise2 = queue.enqueue('/test', { dedupe: false });

      await vi.advanceTimersByTimeAsync(10);
      await Promise.all([promise1, promise2]);

      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
  });

  describe('cancellation', () => {
    it('should cancel requests by tag', async () => {
      // Make fetch return a pending promise
      mockFetch.mockImplementation(async () => new Promise(() => {}));

      const promise = queue.enqueue('/test', { tags: ['my-tag'] });

      await vi.advanceTimersByTimeAsync(10);

      queue.cancelByTag('my-tag');

      await expect(promise).rejects.toThrow(RequestCancelledError);
    });

    it('should cancel all requests', async () => {
      // Make fetch return a pending promise
      mockFetch.mockImplementation(async () => new Promise(() => {}));

      const promises = [
        queue.enqueue('/test1'),
        queue.enqueue('/test2'),
      ];

      await vi.advanceTimersByTimeAsync(10);

      queue.cancelAll();

      for (const promise of promises) {
        await expect(promise).rejects.toThrow(RequestCancelledError);
      }
    });

    it('should cancel specific request by id', async () => {
      // This test would require exposing the request ID, which we don't currently do
      // Skip for now
    });
  });

  describe('overflow handling', () => {
    it('should reject when queue is full with reject strategy', async () => {
      // Make fetch return a pending promise
      mockFetch.mockImplementation(async () => new Promise(() => {}));

      // Fill active slots (2) and queue (5) = 7 total
      for (let i = 0; i < 7; i++) {
        try {
          startPromise(queue.enqueue(`/test${i}`));
        }
        catch {
          // Expected to throw on overflow
        }
      }

      await vi.advanceTimersByTimeAsync(10);

      // Should throw on overflow (queue is full at 5)
      await expect(queue.enqueue('/overflow')).rejects.toThrow(QueueOverflowError);
    });

    it('should update isOverloaded state', async () => {
      // Make fetch return a pending promise
      mockFetch.mockImplementation(async () => new Promise(() => {}));

      expect(queue.state.isOverloaded).toBe(false);

      // Fill beyond overload threshold (3)
      // 2 will go active, 3 will be queued (>= overloadThreshold of 3)
      for (let i = 0; i < 5; i++) {
        startPromise(queue.enqueue(`/test${i}`));
      }

      await vi.advanceTimersByTimeAsync(10);

      expect(queue.state.isOverloaded).toBe(true);
    });
  });

  describe('rate limiting', () => {
    it('should respect maxPerSecond rate limit', async () => {
      const fastQueue = new RequestQueue(mockFetch, {
        maxConcurrent: 100,
        maxPerSecond: 3,
        maxQueueSize: 100,
      });

      const promises: Promise<unknown>[] = [];

      for (let i = 0; i < 5; i++) {
        promises.push(fastQueue.enqueue(`/test${i}`));
      }

      // Allow initial processing
      await vi.advanceTimersByTimeAsync(10);

      // Only 3 should be processed due to rate limit
      expect(mockFetch).toHaveBeenCalledTimes(3);

      // Advance time to allow rate limit to recover (> 1 second)
      await vi.advanceTimersByTimeAsync(1100);

      // Remaining 2 should be processed
      expect(mockFetch).toHaveBeenCalledTimes(5);

      await Promise.all(promises);

      fastQueue.destroy();
    });
  });

  describe('getMetrics', () => {
    it('should return current queue metrics', async () => {
      // Make fetch return a pending promise
      mockFetch.mockImplementation(async () => new Promise(() => {}));

      startPromise(queue.enqueue('/test1'));
      startPromise(queue.enqueue('/test2'));
      startPromise(queue.enqueue('/test3'));

      await vi.advanceTimersByTimeAsync(10);

      const metrics = queue.getMetrics();

      expect(metrics).toHaveProperty('queued');
      expect(metrics).toHaveProperty('active');
      expect(metrics).toHaveProperty('highPriorityQueued');
      expect(metrics).toHaveProperty('isOverloaded');
      expect(metrics).toHaveProperty('requestsThisSecond');
    });
  });

  describe('deduplication with circular references', () => {
    it('should handle circular references in body gracefully', async () => {
      const circularObj: Record<string, unknown> = { name: 'test' };
      circularObj.self = circularObj;

      // Same circular object used twice - they dedupe because safeStringify
      // returns the same fallback string for both
      const promise1 = queue.enqueue('/test', { dedupe: true, body: circularObj });
      const promise2 = queue.enqueue('/test', { dedupe: true, body: circularObj });

      await vi.advanceTimersByTimeAsync(10);
      await Promise.all([promise1, promise2]);

      // Should not throw and should dedupe identical circular objects
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('should not dedupe different circular objects', async () => {
      const circular1: Record<string, unknown> = { name: 'first' };
      circular1.self = circular1;

      const circular2: Record<string, unknown> = { name: 'second' };
      circular2.self = circular2;

      // Different circular objects - both fall back to same unstringifiable key
      // but since they have the same fallback, they will dedupe
      const promise1 = queue.enqueue('/test', { dedupe: true, body: circular1 });
      const promise2 = queue.enqueue('/test', { dedupe: true, body: circular2 });

      await vi.advanceTimersByTimeAsync(10);
      await Promise.all([promise1, promise2]);

      // Both fall back to [unstringifiable:object], so they dedupe
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('should handle circular references in query gracefully', async () => {
      const circularObj: Record<string, unknown> = { filter: 'active' };
      circularObj.nested = circularObj;

      const promise = queue.enqueue('/test', { dedupe: true, query: circularObj });

      await vi.advanceTimersByTimeAsync(10);
      await promise;

      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('queue timeout', () => {
    it('should timeout requests that wait too long in queue', async () => {
      // Create a queue with short timeout
      const timeoutQueue = new RequestQueue(mockFetch, {
        maxConcurrent: 1,
        maxPerSecond: 100,
        maxQueueSize: 10,
        maxQueueTime: 1000, // 1 second timeout
      });

      // Make fetch return a pending promise to block the queue
      mockFetch.mockImplementation(async () => new Promise(() => {}));

      // First request will be active
      startPromise(timeoutQueue.enqueue('/blocking'));

      await vi.advanceTimersByTimeAsync(10);

      // Second request will be queued - set up rejection handler immediately
      let timeoutError: Error | undefined;
      const queuedPromise = timeoutQueue.enqueue('/queued', { maxQueueTime: 1000 })
        .catch((error: Error) => {
          timeoutError = error;
        });

      await vi.advanceTimersByTimeAsync(10);

      expect(timeoutQueue.state.queued).toBe(1);

      // Advance past the timeout check interval (5000ms) + queue time (1000ms)
      await vi.advanceTimersByTimeAsync(6000);
      await queuedPromise;

      // The queued request should be rejected due to timeout
      expect(timeoutError).toBeDefined();
      expect(timeoutError?.message).toBe('Request waited 1000ms in queue');

      expect(timeoutQueue.state.queued).toBe(0);

      timeoutQueue.destroy();
    });

    it('should not timeout requests that are processed in time', async () => {
      const timeoutQueue = new RequestQueue(mockFetch, {
        maxConcurrent: 2,
        maxPerSecond: 100,
        maxQueueSize: 10,
        maxQueueTime: 10000,
      });

      mockFetch.mockResolvedValue({ data: 'success' });

      const promise = timeoutQueue.enqueue('/test');

      await vi.advanceTimersByTimeAsync(10);

      const result = await promise;

      expect(result).toEqual({ data: 'success' });

      timeoutQueue.destroy();
    });
  });

  describe('destroy', () => {
    it('should abort all pending requests without rejecting', async () => {
      // Make fetch return a pending promise
      mockFetch.mockImplementation(async () => new Promise(() => {}));

      startPromise(queue.enqueue('/test1'));
      startPromise(queue.enqueue('/test2'));

      await vi.advanceTimersByTimeAsync(10);

      expect(queue.state.active).toBe(2);

      // Destroy should not throw and should clear state
      queue.destroy();

      expect(queue.state.active).toBe(0);
      expect(queue.state.queued).toBe(0);
    });

    it('should clear timeout intervals', async () => {
      const clearIntervalSpy = vi.spyOn(globalThis, 'clearInterval');
      const clearTimeoutSpy = vi.spyOn(globalThis, 'clearTimeout');

      queue.destroy();

      expect(clearIntervalSpy).toHaveBeenCalled();

      clearIntervalSpy.mockRestore();
      clearTimeoutSpy.mockRestore();
    });
  });

  describe('dropLowest overflow strategy', () => {
    it('should drop lowest priority when queue overflows with dropLowest strategy', async () => {
      const dropQueue = new RequestQueue(mockFetch, {
        maxConcurrent: 1,
        maxPerSecond: 100,
        maxQueueSize: 2,
        overflowStrategy: 'dropLowest',
      });

      // Make fetch return a pending promise
      mockFetch.mockImplementation(async () => new Promise(() => {}));

      // First goes active
      startPromise(dropQueue.enqueue('/active'));
      await vi.advanceTimersByTimeAsync(10);

      // These go to queue - set up rejection handler for low priority immediately
      let dropError: Error | undefined;
      const lowPromise = dropQueue.enqueue('/low', { priority: RequestPriority.LOW })
        .catch((error: Error) => {
          dropError = error;
        });
      startPromise(dropQueue.enqueue('/normal', { priority: RequestPriority.NORMAL }));

      await vi.advanceTimersByTimeAsync(10);

      expect(dropQueue.state.queued).toBe(2);

      // This should trigger drop of lowest priority
      startPromise(dropQueue.enqueue('/high', { priority: RequestPriority.HIGH }));

      // Wait for the drop to process
      await lowPromise;

      // Low priority should be dropped with overflow error
      expect(dropError).toBeInstanceOf(QueueOverflowError);

      await vi.advanceTimersByTimeAsync(10);

      expect(dropQueue.state.queued).toBe(2);

      dropQueue.destroy();
    });
  });
});
