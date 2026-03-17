import type { EffectScope } from 'vue';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useIntervalScheduler } from './use-interval-scheduler';

describe('useIntervalScheduler', () => {
  let scope: EffectScope;

  beforeEach(() => {
    scope = effectScope();
    vi.useFakeTimers();
  });

  afterEach(() => {
    scope.stop();
    vi.useRealTimers();
  });

  it('should call callback on each interval tick', async () => {
    const callback = vi.fn().mockResolvedValue(undefined);
    const scheduler = scope.run(() => useIntervalScheduler({ callback, intervalMs: 1000 }))!;

    scheduler.start();

    expect(callback).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(1000);
    expect(callback).toHaveBeenCalledOnce();

    await vi.advanceTimersByTimeAsync(1000);
    expect(callback).toHaveBeenCalledTimes(2);

    scheduler.stop();
  });

  it('should call callback immediately when start is called with immediate=true', async () => {
    const callback = vi.fn().mockResolvedValue(undefined);
    const scheduler = scope.run(() => useIntervalScheduler({ callback, intervalMs: 5000 }))!;

    scheduler.start(true);
    await vi.advanceTimersByTimeAsync(0);

    expect(callback).toHaveBeenCalledOnce();

    scheduler.stop();
  });

  it('should not call callback immediately when start is called with immediate=false', async () => {
    const callback = vi.fn().mockResolvedValue(undefined);
    const scheduler = scope.run(() => useIntervalScheduler({ callback, intervalMs: 5000 }))!;

    scheduler.start(false);
    await vi.advanceTimersByTimeAsync(0);

    expect(callback).not.toHaveBeenCalled();

    scheduler.stop();
  });

  it('should prevent double-start', async () => {
    const callback = vi.fn().mockResolvedValue(undefined);
    const scheduler = scope.run(() => useIntervalScheduler({ callback, intervalMs: 1000 }))!;

    scheduler.start();
    scheduler.start();

    await vi.advanceTimersByTimeAsync(1000);

    expect(callback).toHaveBeenCalledOnce();

    scheduler.stop();
  });

  it('should stop the interval on stop', async () => {
    const callback = vi.fn().mockResolvedValue(undefined);
    const scheduler = scope.run(() => useIntervalScheduler({ callback, intervalMs: 1000 }))!;

    scheduler.start();
    await vi.advanceTimersByTimeAsync(1000);
    expect(callback).toHaveBeenCalledOnce();

    scheduler.stop();
    callback.mockClear();

    await vi.advanceTimersByTimeAsync(5000);
    expect(callback).not.toHaveBeenCalled();
  });

  it('should allow restart after stop', async () => {
    const callback = vi.fn().mockResolvedValue(undefined);
    const scheduler = scope.run(() => useIntervalScheduler({ callback, intervalMs: 1000 }))!;

    scheduler.start();
    scheduler.stop();
    callback.mockClear();

    scheduler.start();
    await vi.advanceTimersByTimeAsync(1000);
    expect(callback).toHaveBeenCalledOnce();

    scheduler.stop();
  });

  it('should handle stop when not started', () => {
    const callback = vi.fn();
    const scheduler = scope.run(() => useIntervalScheduler({ callback, intervalMs: 1000 }))!;

    expect(() => scheduler.stop()).not.toThrow();
  });
});
