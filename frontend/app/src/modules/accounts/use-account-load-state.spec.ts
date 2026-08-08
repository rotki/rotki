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

  // Returning `undefined` rather than a resolved promise is the point: an idle caller must not even
  // yield a microtask, or it reorders everything after it.
  it('should report nothing pending when no read is running', async () => {
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

  // A read that throws must not leave every later waiter stuck on it.
  it('should settle waiters when the read rejects', async () => {
    const { useAccountLoadState } = await importModule();
    const { pending, track } = useAccountLoadState();

    const tracked = track(Promise.reject(new Error('boom')));
    const waiting = pending();
    await expect(tracked).rejects.toThrow('boom');

    await expect(waiting).resolves.toBeUndefined();
    expect(pending()).toBeUndefined();
  });

  // The whole point of the third state: at session start the store is empty rather than partial,
  // and nothing is in flight yet because the load is still awaiting the exchange rates.
  it('should report pending once armed, before any read starts', async () => {
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

    // Armed but not started: a waiter must not be released by the arming itself. Draining the
    // microtask queue is enough — if the gate were already open, `observer` would have run by now.
    await flushPromises();
    expect(settled).toBe(false);

    const tracked = track(read);
    finish();
    await tracked;
    await observer;

    expect(settled).toBe(true);
    expect(pending()).toBeUndefined();
  });

  // 🔴 The deadlock case. A resumed session restores balances without re-reading accounts, so the
  // read the gate was armed for never happens. Without the release the waiter hangs forever.
  it('should release an armed waiter when no read ever happens', async () => {
    const { useAccountLoadState } = await importModule();
    const { arm, pending, release } = useAccountLoadState();

    arm();
    const waiting = pending();
    release();

    await expect(waiting).resolves.toBeUndefined();
    expect(pending()).toBeUndefined();
  });

  // A waiter belongs to the session that armed it; logging out must not strand it on the next user.
  it('should release an armed waiter on reset', async () => {
    const { useAccountLoadState } = await importModule();
    const { arm, pending, reset } = useAccountLoadState();

    arm();
    const waiting = pending();
    reset();

    await expect(waiting).resolves.toBeUndefined();
    expect(pending()).toBeUndefined();
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
