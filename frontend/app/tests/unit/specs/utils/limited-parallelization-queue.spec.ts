import {
  afterAll,
  beforeAll,
  beforeEach,
  expect,
  test,
  vi,
  vitest
} from 'vitest';
import flushPromises from 'flush-promises';
import { LimitedParallelizationQueue } from '@/utils/limited-parallelization-queue';

describe('LimitedParallelizationQueue', () => {
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

  test('runs up to 5 task in parallel', async () => {
    const listener = vi.fn().mockImplementation(() => {});
    queue.setOnCompletion(listener);
    queue.queue('1', () => wait(1500));
    queue.queue('2', () => wait(3000));
    queue.queue('3', () => wait(9800));
    queue.queue('4', () => wait(19800));
    queue.queue('5', () => wait(39800));
    queue.queue('6', () => wait(2800));

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

    queue.queue('1', () => wait(1500));
    expect(queue.pending).toBe(0);
    expect(queue.running).toBe(1);

    vitest.advanceTimersByTime(1500);
    await flushPromises();

    expect(listener).toHaveBeenCalledTimes(2);
  });

  test('new task with the same id becomes pending', async () => {
    queue.queue('1', () => wait(1500));
    queue.queue('1', () => wait(3000));

    expect(queue.running).toBe(1);
    expect(queue.pending).toBe(1);
  });

  test('new pending task replaces pending task with the same id', async () => {
    queue.queue('1', () => wait(1500));
    queue.queue('1', () => wait(3000));
    queue.queue('1', () => wait(4000));

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

  test('clear will remove any pending tasks from the queue', () => {
    queue.queue('1', () => wait(1500));
    queue.queue('1', () => wait(3000));

    expect(queue.running).toBe(1);
    expect(queue.pending).toBe(1);

    queue.clear();

    expect(queue.running).toBe(1);
    expect(queue.pending).toBe(0);
  });
});
