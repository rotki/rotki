import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { delay, waitForCondition } from './async-utilities';

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn() },
}));

describe('delay', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should resolve after the given time', async () => {
    let resolved = false;
    const promise = delay(1000).then(() => {
      resolved = true;
    });
    expect(resolved).toBe(false);
    await vi.advanceTimersByTimeAsync(1000);
    await promise;
    expect(resolved).toBe(true);
  });

  it('should reject immediately when the signal is already aborted', async () => {
    const controller = new AbortController();
    controller.abort();
    await expect(delay(1000, controller.signal)).rejects.toThrow('aborted');
  });

  it('should reject when the signal aborts mid-flight', async () => {
    const controller = new AbortController();
    const promise = delay(1000, controller.signal);
    const assertion = expect(promise).rejects.toThrow('aborted');
    controller.abort();
    await assertion;
  });
});

describe('waitForCondition', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should resolve as soon as the condition is met', async () => {
    const checkFn = vi.fn().mockResolvedValue('ready');
    const result = await waitForCondition(checkFn, r => r === 'ready', { name: 'op' });
    expect(result).toBe('ready');
    expect(checkFn).toHaveBeenCalledTimes(1);
  });

  it('should keep polling until the condition becomes true', async () => {
    const checkFn = vi.fn()
      .mockResolvedValueOnce('pending')
      .mockResolvedValueOnce('done');
    const promise = waitForCondition(checkFn, r => r === 'done', { name: 'op', interval: 500 });
    await vi.advanceTimersByTimeAsync(500);
    await expect(promise).resolves.toBe('done');
    expect(checkFn).toHaveBeenCalledTimes(2);
  });

  it('should retry after a failed check', async () => {
    const checkFn = vi.fn()
      .mockRejectedValueOnce(new Error('boom'))
      .mockResolvedValueOnce('done');
    const promise = waitForCondition(checkFn, r => r === 'done', { name: 'op', interval: 500 });
    await vi.advanceTimersByTimeAsync(500);
    await expect(promise).resolves.toBe('done');
    expect(checkFn).toHaveBeenCalledTimes(2);
  });

  it('should reject with a timeout error when the condition never holds', async () => {
    const checkFn = vi.fn().mockResolvedValue('never');
    const promise = waitForCondition(checkFn, () => false, { name: 'op', interval: 500, timeout: 1000 });
    const assertion = expect(promise).rejects.toThrow(/Timeout waiting for op/);
    await vi.advanceTimersByTimeAsync(1000);
    await assertion;
  });

  it('should reject immediately when the signal is already aborted', async () => {
    const controller = new AbortController();
    controller.abort();
    await expect(
      waitForCondition(vi.fn().mockResolvedValue('x'), () => true, { name: 'op', signal: controller.signal }),
    ).rejects.toThrow('aborted');
  });
});
