import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { delay, waitForCondition, withTimeout } from './async-utilities';

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

describe('withTimeout', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should resolve with the promise value when it settles first', async () => {
    await expect(withTimeout(Promise.resolve('value'), 1000, 'op')).resolves.toBe('value');
  });

  it('should propagate a rejection from the promise rather than timing out', async () => {
    await expect(withTimeout(Promise.reject(new Error('inner')), 1000, 'op')).rejects.toThrow('inner');
  });

  it('should reject with a timeout error naming the operation when the timeout wins', async () => {
    const promise = withTimeout(new Promise(() => {}), 1000, 'ping');
    const assertion = expect(promise).rejects.toThrow('Timeout waiting for ping (1000ms)');
    await vi.advanceTimersByTimeAsync(1000);
    await assertion;
  });

  it('should tag the timeout rejection with the TIMEOUT code', async () => {
    const promise = withTimeout(new Promise(() => {}), 500, 'ping');
    const assertion = expect(promise).rejects.toMatchObject({ code: 'TIMEOUT', name: 'TimeoutError' });
    await vi.advanceTimersByTimeAsync(500);
    await assertion;
  });

  it('should clear the timer once the promise wins, leaving nothing pending', async () => {
    await expect(withTimeout(Promise.resolve('fast'), 1000, 'op')).resolves.toBe('fast');
    expect(vi.getTimerCount()).toBe(0);
  });
});

describe('async utility errors', () => {
  it('should expose the abort code and the operation in the message', async () => {
    const controller = new AbortController();
    controller.abort();
    await expect(delay(10, controller.signal)).rejects.toMatchObject({
      code: 'ABORTED',
      message: 'Operation delay was aborted',
      name: 'AbortedError',
    });
  });

  it('should report the timeout code and operation together', async () => {
    vi.useFakeTimers();
    try {
      const promise = withTimeout(new Promise(() => {}), 100, 'refresh');
      const assertion = expect(promise).rejects.toMatchObject({
        code: 'TIMEOUT',
        message: 'Timeout waiting for refresh (100ms)',
      });
      await vi.advanceTimersByTimeAsync(100);
      await assertion;
    }
    finally {
      vi.useRealTimers();
    }
  });
});
