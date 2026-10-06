import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { beginSession, endSession, hasLiveSession, liveSessionSignal, onSessionCleared, onSessionEnd, scheduleSessionClear } from '@/modules/core/session/session-lifecycle';

describe('session-lifecycle', () => {
  it('should hold no live session and no signal once the session ends', () => {
    endSession();

    expect(hasLiveSession()).toBe(false);
    expect(liveSessionSignal()).toBeUndefined();
  });

  it('should abort the ended session\'s signal', () => {
    beginSession();
    const signal = liveSessionSignal();

    endSession();

    expect(signal?.aborted).toBe(true);
  });

  it('should give a new session a fresh signal and abort the one it replaced', () => {
    beginSession();
    const first = liveSessionSignal();

    beginSession();

    expect(first?.aborted).toBe(true);
    expect(liveSessionSignal()?.aborted).toBe(false);
    expect(hasLiveSession()).toBe(true);
  });

  it('should tell end listeners once per ended session, and not when nothing was live', () => {
    beginSession();
    const listener = vi.fn<() => void>();
    const remove = onSessionEnd('spec', listener);

    endSession();
    endSession();

    expect(listener).toHaveBeenCalledOnce();
    remove();
  });

  it('should replace a listener registered again under the same key, as a re-evaluated module does', () => {
    beginSession();
    const earlier = vi.fn<() => void>();
    const later = vi.fn<() => void>();
    onSessionEnd('spec', earlier);
    const remove = onSessionEnd('spec', later);

    endSession();

    expect(earlier).not.toHaveBeenCalled();
    expect(later).toHaveBeenCalledOnce();
    remove();
  });

  describe('clear phase', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    /** Lets the clear phase, which follows a logout by one task, run. */
    async function nextTask(): Promise<void> {
      await vi.advanceTimersByTimeAsync(0);
    }

    it('should clear one task after a logout, once callers resumed by the end have run', async () => {
      beginSession();
      const order: string[] = [];
      const removeEnd = onSessionEnd('spec', () => order.push('end'));
      const removeClear = onSessionCleared('spec', () => order.push('clear'));

      endSession();
      scheduleSessionClear();
      await Promise.resolve();
      order.push('resumed caller');
      expect(order).toEqual(['end', 'resumed caller']);

      await nextTask();

      expect(order).toEqual(['end', 'resumed caller', 'clear']);
      removeEnd();
      removeClear();
    });

    it('should not clear when a session ends without a logout, as a failed unlock does', async () => {
      beginSession();
      const clear = vi.fn<() => void>();
      const remove = onSessionCleared('spec', clear);

      endSession();
      await nextTask();
      beginSession();

      expect(clear).not.toHaveBeenCalled();
      remove();
    });

    it('should run a pending clear before the next session begins, if its task has not come yet', () => {
      beginSession();
      const clear = vi.fn<() => void>();
      const remove = onSessionCleared('spec', clear);

      endSession();
      scheduleSessionClear();
      beginSession();

      expect(clear).toHaveBeenCalledOnce();
      expect(hasLiveSession()).toBe(true);
      remove();
    });

    it('should clear once however often it is scheduled', async () => {
      beginSession();
      const clear = vi.fn<() => void>();
      const remove = onSessionCleared('spec', clear);

      endSession();
      scheduleSessionClear();
      scheduleSessionClear();
      await nextTask();
      beginSession();

      expect(clear).toHaveBeenCalledOnce();
      remove();
    });
  });

  it('should keep one session across a second evaluation of the module', async () => {
    beginSession();
    vi.resetModules();

    const reloaded = await import('@/modules/core/session/session-lifecycle');

    expect(reloaded.hasLiveSession()).toBe(true);
    reloaded.endSession();
    expect(hasLiveSession()).toBe(false);
  });
});
