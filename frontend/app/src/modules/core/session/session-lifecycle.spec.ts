import { describe, expect, it, vi } from 'vitest';
import { beginSession, endSession, hasLiveSession, liveSessionSignal, onSessionEnd } from '@/modules/core/session/session-lifecycle';

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

  it('should keep one session across a second evaluation of the module', async () => {
    beginSession();
    vi.resetModules();

    const reloaded = await import('@/modules/core/session/session-lifecycle');

    expect(reloaded.hasLiveSession()).toBe(true);
    reloaded.endSession();
    expect(hasLiveSession()).toBe(false);
  });
});
