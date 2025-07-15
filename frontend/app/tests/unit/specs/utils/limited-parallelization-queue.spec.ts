import { wait } from '@shared/utils';
import flushPromises from 'flush-promises';
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi, vitest } from 'vitest';
import { LimitedParallelizationQueue } from '@/utils/limited-parallelization-queue';

describe('limitedParallelizationQueue', () => {
  let queue: LimitedParallelizationQueue;

  beforeAll(() => {
    vitest.useFakeTimers();
  });

  beforeEach(() => {
    queue = new LimitedParallelizationQueue();
  });

  afterAll(() => {
    vitest.useRealTimers();
  });

  it('runs up to 5 task in parallel', async () => {
    const listener = vi.fn().mockImplementation(() => {});
    queue.setOnCompletion(listener);
    queue.queue('1', async () => wait(1500));
    queue.queue('2', async () => wait(3000));
    queue.queue('3', async () => wait(9800));
    queue.queue('4', async () => wait(19800));
    queue.queue('5', async () => wait(39800));
    queue.queue('6', async () => wait(2800));

    expect(queue.pending).toBe(1);
    expect(queue.running).toBe(5);

    vitest.advanceTimersByTime(3000);
    await flushPromises();

    expect(listener).toHaveBeenCalledTimes(0);

    expect(queue.pending).toBe(0);
    expect(queue.running).toBe(4);

    vitest.advanceTimersByTime(40000);
    await flushPromises();

    expect(queue.pending).toBe(0);
    expect(queue.running).toBe(0);

    expect(listener).toHaveBeenCalledTimes(1);

    queue.queue('1', async () => wait(1500));
    expect(queue.pending).toBe(0);
    expect(queue.running).toBe(1);

    vitest.advanceTimersByTime(1500);
    await flushPromises();

    expect(listener).toHaveBeenCalledTimes(2);
  });

  it('new task with the same id becomes pending', () => {
    queue.queue('1', async () => wait(1500));
    queue.queue('1', async () => wait(3000));

    expect(queue.running).toBe(1);
    expect(queue.pending).toBe(1);
  });

  it('new pending task replaces pending task with the same id', async () => {
    queue.queue('1', async () => wait(1500));
    queue.queue('1', async () => wait(3000));
    queue.queue('1', async () => wait(4000));

    expect(queue.running).toBe(1);
    expect(queue.pending).toBe(1);

    vitest.advanceTimersByTime(1500);
    await flushPromises();

    expect(queue.running).toBe(1);
    expect(queue.pending).toBe(0);

    vitest.advanceTimersByTime(3000);
    await flushPromises();

    expect(queue.running).toBe(1);
  });

  it('clear will remove any pending tasks from the queue', () => {
    queue.queue('1', async () => wait(1500));
    queue.queue('1', async () => wait(3000));

    expect(queue.running).toBe(1);
    expect(queue.pending).toBe(1);

    queue.clear();

    expect(queue.running).toBe(1);
    expect(queue.pending).toBe(0);
  });
});
