import { flushPromises } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

async function importModule(): Promise<typeof import('./use-account-load-state')> {
  return import('./use-account-load-state');
}

describe('useAccountLoadState', () => {
  beforeEach(() => {
    // `createSharedComposable` keeps one instance per module, so each test needs a fresh module.
    vi.resetModules();
  });

  it('should report nothing pending when no read is running, returning undefined rather than a resolved promise so an idle caller does not even yield a microtask', async () => {
    const { useAccountLoadState } = await importModule();

    expect(useAccountLoadState().pending()).toBeUndefined();
  });

  it('should report a running read as pending until it finishes', async () => {
    const { useAccountLoadState } = await importModule();
    const { pending, track } = useAccountLoadState();
    let finish = (): void => {};
    const read = new Promise<void>((resolve) => {
      finish = resolve;
    });

    const tracked = track(read);
    expect(pending()).toBeDefined();

    finish();
    await tracked;
    expect(pending()).toBeUndefined();
  });

  it('should settle waiters when the read rejects, rather than stranding every later one', async () => {
    const { useAccountLoadState } = await importModule();
    const { pending, track } = useAccountLoadState();

    const tracked = track(Promise.reject(new Error('boom')));
    const waiting = pending();
    await expect(tracked).rejects.toThrow('boom');

    await expect(waiting).resolves.toBeUndefined();
    expect(pending()).toBeUndefined();
  });

  it('should report pending once armed, before any read starts, since at session start the store is empty rather than partial', async () => {
    const { useAccountLoadState } = await importModule();
    const { arm, pending } = useAccountLoadState();

    expect(pending()).toBeUndefined();
    arm();
    expect(pending()).toBeDefined();
  });

  it('should keep an armed waiter waiting until the first read finishes', async () => {
    const { useAccountLoadState } = await importModule();
    const { arm, pending, track } = useAccountLoadState();
    let finish = (): void => {};
    const read = new Promise<void>((resolve) => {
      finish = resolve;
    });

    arm();
    const waiting = pending();
    let settled = false;
    const observer = waiting?.then(() => {
      settled = true;
    });

    await flushPromises();
    expect(settled).toBe(false);

    const tracked = track(read);
    finish();
    await tracked;
    await observer;

    expect(settled).toBe(true);
    expect(pending()).toBeUndefined();
  });

  it('should release an armed waiter when no read ever happens, as on a resumed session that restores balances without re-reading accounts', async () => {
    const { useAccountLoadState } = await importModule();
    const { arm, pending, release } = useAccountLoadState();

    arm();
    const waiting = pending();
    release();

    await expect(waiting).resolves.toBeUndefined();
    expect(pending()).toBeUndefined();
  });

  it('should release an armed waiter on reset, it belonging to the session that armed it', async () => {
    const { useAccountLoadState } = await importModule();
    const { arm, pending, reset } = useAccountLoadState();

    arm();
    const waiting = pending();
    reset();

    await expect(waiting).resolves.toBeUndefined();
    expect(pending()).toBeUndefined();
  });

  describe('the unstarted-read bound', () => {
    /**
     * `release()` normally ends the wait, but its caller sits behind
     * `allSettled([fetchCached(), …])`, and `allSettled` cannot settle if `fetchCached` never does.
     * Observed in the app: a poisoned `prices:exchange-rates` id stalled `fetchCached` on its first
     * await, and the history sync waited forever.
     */
    it('should release a gate whose read never starts', async () => {
      vi.useFakeTimers();
      const { useAccountLoadState } = await importModule();
      const { arm, pending } = useAccountLoadState();

      arm();
      const waiting = pending();
      await vi.advanceTimersByTimeAsync(30_000);

      await expect(waiting).resolves.toBeUndefined();
      expect(pending()).toBeUndefined();
      vi.useRealTimers();
    });

    /**
     * The bound covers "promised but never started" only. A read that is genuinely in flight must
     * be waited out however long it takes — expiring mid-read releases waiters into a half-filled
     * store, which is the bug this composable exists to prevent.
     */
    it('should not expire while a read is actually in flight', async () => {
      vi.useFakeTimers();
      const { useAccountLoadState } = await importModule();
      const { arm, pending, track } = useAccountLoadState();
      let finish = (): void => {};
      const read = new Promise<void>((resolve) => {
        finish = resolve;
      });

      arm();
      const tracked = track(read);
      const wellPastTheBound = 120_000;
      await vi.advanceTimersByTimeAsync(wellPastTheBound);
      expect(pending()).toBeDefined();

      finish();
      await tracked;
      expect(pending()).toBeUndefined();
      vi.useRealTimers();
    });

    it('should not fire after the gate was already released', async () => {
      vi.useFakeTimers();
      const { useAccountLoadState } = await importModule();
      const { arm, pending, release } = useAccountLoadState();

      arm();
      release();
      await vi.advanceTimersByTimeAsync(30_000);

      // A late timer must not resurrect or re-settle anything.
      expect(pending()).toBeUndefined();
      vi.useRealTimers();
    });
  });

  it('should join a second arm to the waiter the first one created', async () => {
    const { useAccountLoadState } = await importModule();
    const { arm, pending, release } = useAccountLoadState();

    arm();
    const first = pending();
    arm();
    expect(pending()).toBe(first);

    release();
    await expect(first).resolves.toBeUndefined();
  });

  it('should track the newer read when one starts while another is finishing', async () => {
    const { useAccountLoadState } = await importModule();
    const { pending, track } = useAccountLoadState();
    let finishFirst = (): void => {};
    const first = new Promise<void>((resolve) => {
      finishFirst = resolve;
    });

    const trackedFirst = track(first);
    const trackedSecond = track(Promise.resolve());
    await trackedSecond;

    // The first settling must not clear the entry the second one owns.
    finishFirst();
    await trackedFirst;
    expect(pending()).toBeUndefined();
  });
});
