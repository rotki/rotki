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
