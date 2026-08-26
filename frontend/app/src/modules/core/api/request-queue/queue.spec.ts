import { startPromise } from '@shared/utils';
import { afterEach, beforeEach, describe, expect, it, type MockedFunction, vi } from 'vitest';
import { QueueOverflowError, RequestCancelledError } from './errors';
import { type QueueFetchFn, RequestQueue } from './queue';
import { RequestPriority } from './request-priority';

const ACTIVE_SLOTS = 2;
const QUEUE_SLOTS = 5;
const OVERLOAD_THRESHOLD = 3;
const CAPACITY = ACTIVE_SLOTS + QUEUE_SLOTS;

/** How often the queue sweeps for entries that have waited past their `maxQueueTime`. */
const TIMEOUT_SWEEP_INTERVAL_MS = 5000;
const MAX_QUEUE_TIME_MS = 1000;

describe('requestQueue', () => {
  let queue: RequestQueue;
  let mockFetch: MockedFunction<QueueFetchFn>;

  const mockFetchWrapper = async <T>(
    url: string,
    options?: Record<string, unknown>,
  ): Promise<T> => {
    const result = await mockFetch(url, options);
    // @ts-expect-error mock returns unknown but generic wrapper needs T
    return result;
  };

  beforeEach(() => {
    vi.useFakeTimers();
    mockFetch = vi.fn().mockResolvedValue({ data: 'success' });
    queue = new RequestQueue(mockFetchWrapper, {
      maxConcurrent: ACTIVE_SLOTS,
      maxPerSecond: 10,
      maxQueueSize: QUEUE_SLOTS,
      maxQueueTime: 5000,
      overloadThreshold: OVERLOAD_THRESHOLD,
    });
  });

  afterEach(() => {
    queue.destroy();
    vi.useRealTimers();
  });

  describe('basic functionality', () => {
    it('should process a single request', async () => {
      const promise = queue.enqueue('/test');

      await vi.advanceTimersByTimeAsync(10);

      const result = await promise;

      expect(mockFetch).toHaveBeenCalledWith('/test', expect.any(Object));
      expect(result).toEqual({ data: 'success' });
    });

    it('should process multiple requests in parallel up to maxConcurrent', async () => {
      const resolvers: Array<(value: { data: string }) => void> = [];
      mockFetch.mockImplementation(async () => new Promise((resolve) => {
        resolvers.push(resolve);
      }));

      const promises = [
        queue.enqueue('/test1'),
        queue.enqueue('/test2'),
        queue.enqueue('/test3'),
      ];

      await vi.advanceTimersByTimeAsync(10);

      expect(queue.state.active).toBe(2);
      expect(queue.state.queued).toBe(1);

      resolvers[0]({ data: 'done' });
      resolvers[1]({ data: 'done' });
      await vi.advanceTimersByTimeAsync(10);

      expect(resolvers).toHaveLength(3);

      resolvers[2]({ data: 'done' });
      await vi.advanceTimersByTimeAsync(10);

      await Promise.all(promises);

      expect(mockFetch).toHaveBeenCalledTimes(3);
    });

    it('should update state correctly', async () => {
      expect(queue.state.queued).toBe(0);
      expect(queue.state.active).toBe(0);

      let resolver: (value: { data: string }) => void;
      mockFetch.mockImplementation(async () => new Promise((resolve) => {
        resolver = resolve;
      }));

      const promise = queue.enqueue('/test');

      await vi.advanceTimersByTimeAsync(10);

      expect(queue.state.active).toBe(1);

      resolver!({ data: 'done' });
      await vi.advanceTimersByTimeAsync(10);
      await promise;

      expect(queue.state.active).toBe(0);
    });
  });

  describe('priority handling', () => {
    it('should process high priority requests first', async () => {
      const order: string[] = [];

      const resolvers: Map<string, (value: { data: string }) => void> = new Map();
      mockFetch.mockImplementation(async (url: string) => {
        order.push(url);
        return new Promise((resolve) => {
          resolvers.set(url, resolve);
        });
      });

      startPromise(queue.enqueue('/first1'));
      startPromise(queue.enqueue('/first2'));

      await vi.advanceTimersByTimeAsync(10);

      expect(queue.state.active).toBe(2);

      startPromise(queue.enqueue('/low', { priority: RequestPriority.LOW }));
      startPromise(queue.enqueue('/high', { priority: RequestPriority.HIGH }));
      startPromise(queue.enqueue('/normal', { priority: RequestPriority.NORMAL }));

      resolvers.get('/first1')!({ data: 'done' });
      resolvers.get('/first2')!({ data: 'done' });

      await vi.advanceTimersByTimeAsync(10);

      expect(order).toContain('/high');
      expect(order).toContain('/normal');

      resolvers.get('/high')!({ data: 'done' });
      resolvers.get('/normal')!({ data: 'done' });

      await vi.advanceTimersByTimeAsync(10);

      expect(order).toContain('/low');

      expect(order.indexOf('/high')).toBeLessThan(order.indexOf('/low'));
      expect(order.indexOf('/normal')).toBeLessThan(order.indexOf('/low'));
    });
  });

  describe('retry backoff', () => {
    it('should release the slot while a request waits to be retried', async () => {
      const started: string[] = [];
      const retrying = new RequestQueue(mockFetchWrapper, {
        maxConcurrent: 1,
        maxPerSecond: 100,
        maxRetries: 1,
        retryDelay: 1000,
      });

      mockFetch.mockImplementation(async (url: string) => {
        started.push(url);
        if (url === '/flaky' && started.filter(u => u === '/flaky').length === 1)
          throw new TypeError('network down');

        return new Promise(() => {}); // holds the slot once it does run
      });

      startPromise(retrying.enqueue('/flaky').catch(() => {}));
      await vi.advanceTimersByTimeAsync(10);
      expect(started).toEqual(['/flaky']);

      // Still inside the 1000ms backoff: the slot the retry is waiting for must be usable.
      startPromise(retrying.enqueue('/other'));
      await vi.advanceTimersByTimeAsync(10);

      expect(started).toContain('/other');

      retrying.destroy();
    });
  });

  describe('background slot cap', () => {
    /**
     * Six identical ENS reverse lookups once hung for ~100s each and filled every slot, so the
     * DELETE behind a user's confirmed delete never left the queue and the app went silent
     * (seen in the history-events e2e spec, CI only). Priority cannot fix that alone: it orders the
     * queue, and by then there was nothing left to order. Background work must not be able to take
     * the whole budget in the first place.
     */
    it('should keep a slot for other work while background requests hang', async () => {
      const started: string[] = [];
      mockFetch.mockImplementation(async (url: string) => {
        started.push(url);
        return new Promise(() => {}); // never settles, like the hanging lookups
      });

      const capped = new RequestQueue(mockFetchWrapper, {
        maxBackgroundConcurrent: 2,
        maxConcurrent: 6,
        maxPerSecond: 100,
      });

      for (let i = 0; i < 6; i++)
        startPromise(capped.enqueue(`/background${i}`, { priority: RequestPriority.LOW }));

      await vi.advanceTimersByTimeAsync(10);

      expect(started).toHaveLength(2);

      startPromise(capped.enqueue('/user-action', { priority: RequestPriority.CRITICAL }));
      await vi.advanceTimersByTimeAsync(10);

      expect(started).toContain('/user-action');

      capped.destroy();
    });

    it('should let background requests use every slot when nothing competes', async () => {
      const started: string[] = [];
      mockFetch.mockImplementation(async (url: string) => {
        started.push(url);
        return new Promise(() => {});
      });

      const capped = new RequestQueue(mockFetchWrapper, {
        maxBackgroundConcurrent: 2,
        maxConcurrent: 6,
        maxPerSecond: 100,
      });

      for (let i = 0; i < 4; i++)
        startPromise(capped.enqueue(`/normal${i}`, { priority: RequestPriority.NORMAL }));

      await vi.advanceTimersByTimeAsync(10);
      expect(started).toHaveLength(4);

      capped.destroy();
    });

    it('should release the cap as background requests finish', async () => {
      const started: string[] = [];
      const resolvers = new Map<string, (value: { data: string }) => void>();
      mockFetch.mockImplementation(async (url: string) => {
        started.push(url);
        return new Promise((resolve) => {
          resolvers.set(url, resolve);
        });
      });

      const capped = new RequestQueue(mockFetchWrapper, {
        maxBackgroundConcurrent: 2,
        maxConcurrent: 6,
        maxPerSecond: 100,
      });

      for (let i = 0; i < 3; i++)
        startPromise(capped.enqueue(`/background${i}`, { priority: RequestPriority.LOW }));

      await vi.advanceTimersByTimeAsync(10);
      expect(started).toHaveLength(2);

      resolvers.get('/background0')!({ data: 'done' });
      await vi.advanceTimersByTimeAsync(10);

      expect(started).toContain('/background2');

      capped.destroy();
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
      mockFetch.mockImplementation(async () => new Promise(() => {}));

      const promise = queue.enqueue('/test', { tags: ['my-tag'] });

      await vi.advanceTimersByTimeAsync(10);

      queue.cancelByTag('my-tag');

      await expect(promise).rejects.toThrow(RequestCancelledError);
    });

    it('should cancel all requests', async () => {
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

    // Blocked on the queue exposing a request id; an empty body would report green instead.
    it.todo('should cancel specific request by id');
  });

  describe('overflow handling', () => {
    it('should reject when queue is full with reject strategy', async () => {
      mockFetch.mockImplementation(async () => new Promise(() => {}));

      for (let i = 0; i < CAPACITY; i++) {
        startPromise(queue.enqueue(`/test${i}`));
      }

      await vi.advanceTimersByTimeAsync(10);

      await expect(queue.enqueue('/overflow')).rejects.toThrow(QueueOverflowError);
    });

    it('should update isOverloaded state', async () => {
      mockFetch.mockImplementation(async () => new Promise(() => {}));

      expect(queue.state.isOverloaded).toBe(false);

      for (let i = 0; i < ACTIVE_SLOTS + OVERLOAD_THRESHOLD; i++) {
        startPromise(queue.enqueue(`/test${i}`));
      }

      await vi.advanceTimersByTimeAsync(10);

      expect(queue.state.isOverloaded).toBe(true);
    });
  });

  describe('rate limiting', () => {
    it('should respect maxPerSecond rate limit', async () => {
      const fastQueue = new RequestQueue(mockFetchWrapper, {
        maxConcurrent: 100,
        maxPerSecond: 3,
        maxQueueSize: 100,
      });

      const promises: Promise<unknown>[] = [];

      for (let i = 0; i < 5; i++) {
        promises.push(fastQueue.enqueue(`/test${i}`));
      }

      await vi.advanceTimersByTimeAsync(10);

      expect(mockFetch).toHaveBeenCalledTimes(3);

      // Past the one-second window, so the rate limit has recovered.
      await vi.advanceTimersByTimeAsync(1100);

      expect(mockFetch).toHaveBeenCalledTimes(5);

      await Promise.all(promises);

      fastQueue.destroy();
    });
  });

  describe('getMetrics', () => {
    it('should return current queue metrics', async () => {
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

      // `safeStringify` answers the same fallback string for anything it cannot serialise, which
      // is what makes two circular bodies dedupe onto one request.
      const promise1 = queue.enqueue('/test', { dedupe: true, body: circularObj });
      const promise2 = queue.enqueue('/test', { dedupe: true, body: circularObj });

      await vi.advanceTimersByTimeAsync(10);
      await Promise.all([promise1, promise2]);

      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('should not dedupe different circular objects', async () => {
      const circular1: Record<string, unknown> = { name: 'first' };
      circular1.self = circular1;

      const circular2: Record<string, unknown> = { name: 'second' };
      circular2.self = circular2;

      const promise1 = queue.enqueue('/test', { dedupe: true, body: circular1 });
      const promise2 = queue.enqueue('/test', { dedupe: true, body: circular2 });

      await vi.advanceTimersByTimeAsync(10);
      await Promise.all([promise1, promise2]);

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
      const timeoutQueue = new RequestQueue(mockFetchWrapper, {
        maxConcurrent: 1,
        maxPerSecond: 100,
        maxQueueSize: 10,
        maxQueueTime: MAX_QUEUE_TIME_MS,
      });

      mockFetch.mockImplementation(async () => new Promise(() => {}));

      startPromise(timeoutQueue.enqueue('/blocking'));

      await vi.advanceTimersByTimeAsync(10);

      let timeoutError: Error | undefined;
      const queuedPromise = timeoutQueue.enqueue('/queued', { maxQueueTime: MAX_QUEUE_TIME_MS })
        .catch((error: Error) => {
          timeoutError = error;
        });

      await vi.advanceTimersByTimeAsync(10);

      expect(timeoutQueue.state.queued).toBe(1);

      await vi.advanceTimersByTimeAsync(TIMEOUT_SWEEP_INTERVAL_MS + MAX_QUEUE_TIME_MS);
      await queuedPromise;

      expect(timeoutError).toBeDefined();
      expect(timeoutError?.message).toBe(`Request waited ${MAX_QUEUE_TIME_MS}ms in queue`);

      expect(timeoutQueue.state.queued).toBe(0);

      timeoutQueue.destroy();
    });

    it('should not timeout requests that are processed in time', async () => {
      const timeoutQueue = new RequestQueue(mockFetchWrapper, {
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
      mockFetch.mockImplementation(async () => new Promise(() => {}));

      startPromise(queue.enqueue('/test1'));
      startPromise(queue.enqueue('/test2'));

      await vi.advanceTimersByTimeAsync(10);

      expect(queue.state.active).toBe(2);

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
      const dropQueue = new RequestQueue(mockFetchWrapper, {
        maxConcurrent: 1,
        maxPerSecond: 100,
        maxQueueSize: 2,
        overflowStrategy: 'dropLowest',
      });

      mockFetch.mockImplementation(async () => new Promise(() => {}));

      startPromise(dropQueue.enqueue('/active'));
      await vi.advanceTimersByTimeAsync(10);

      // The handler is attached before the drop, or the rejection lands unhandled.
      let dropError: Error | undefined;
      const lowPromise = dropQueue.enqueue('/low', { priority: RequestPriority.LOW })
        .catch((error: Error) => {
          dropError = error;
        });
      startPromise(dropQueue.enqueue('/normal', { priority: RequestPriority.NORMAL }));

      await vi.advanceTimersByTimeAsync(10);

      expect(dropQueue.state.queued).toBe(2);

      startPromise(dropQueue.enqueue('/high', { priority: RequestPriority.HIGH }));

      await lowPromise;

      expect(dropError).toBeInstanceOf(QueueOverflowError);

      await vi.advanceTimersByTimeAsync(10);

      expect(dropQueue.state.queued).toBe(2);

      dropQueue.destroy();
    });
  });
});
