interface UseAccountLoadStateReturn {
  arm: () => void;
  release: () => void;
  track: (load: Promise<void>) => Promise<void>;
  pending: () => Promise<void> | undefined;
  reset: () => void;
}

/**
 * Whether the account store can be trusted to be complete, and a way to wait until it is.
 *
 * The store is filled one chain at a time, so anything that snapshots the account set while a read
 * is running sees a partial one. The history sync freezes that snapshot as its scope, which silently
 * drops the chains that have not arrived yet.
 *
 * ⚠️ This hands out a promise for *timing*, never for data. A caller that needs accounts must read
 * them itself afterwards.
 *
 * ⭐ There are three states, not two, and the third is the one that matters. Tracking only the
 * in-flight read answers "is a read running?", when the question a consumer is really asking is
 * "has a read happened yet?". Those differ in exactly one window — session start — which is the
 * only window where the store is empty rather than partial. The window is wide: `fetchCached()`
 * awaits the exchange rates before it ever calls `refreshAccounts()`, and for that whole round trip
 * nothing is in flight, so an in-flight-only gate is a no-op over an empty store.
 *
 * 🔴 Blocking on "not started yet" is where a deadlock becomes possible, so arming is explicit and
 * every arm is paired with a guaranteed {@link release}: the session decides up front whether a
 * read is coming, and says so. Not every session loads accounts — a resumed one restores balances
 * without re-reading them — and a gate armed by hope would wait forever on exactly those.
 */
export const useAccountLoadState = createSharedComposable((): UseAccountLoadStateReturn => {
  let current: Promise<void> | undefined;
  let gate: Promise<void> | undefined;
  let openGate: (() => void) | undefined;

  /**
   * Resolves the gate rather than dropping it: a waiter holds the promise itself, so replacing the
   * reference without resolving it would strand that waiter for the life of the process.
   */
  const settle = (): void => {
    openGate?.();
    gate = undefined;
    openGate = undefined;
  };

  /**
   * Declares that a full read is coming, before the first `await` on the way to it. Idempotent, so
   * a second caller joins the existing gate instead of replacing one that already has waiters.
   */
  const arm = (): void => {
    gate ??= new Promise<void>((resolve) => {
      openGate = resolve;
    });
  };

  /**
   * Ends the wait without a read having happened. The counterpart to {@link arm} for the paths that
   * turn out not to load accounts, and the safety net for a load that dies before reaching
   * {@link track}.
   */
  const release = (): void => {
    settle();
  };

  const track = async (load: Promise<void>): Promise<void> => {
    // Settles on rejection too, so a failed read cannot leave a waiter stuck forever.
    const tracked = load.finally(() => {
      if (current === tracked)
        current = undefined;

      // The first read to finish opens the gate: from here the store is as complete as this session
      // is going to make it, and a later targeted read is scoped to what it changed.
      settle();
    });
    current = tracked;
    return tracked;
  };

  /**
   * ⚠️ Returns `undefined` rather than a resolved promise once accounts are ready, so an idle caller
   * does not even yield a microtask. Awaiting unconditionally reorders everything after it.
   *
   * The rejection is swallowed: a waiter only cares that the read finished, not that it worked.
   */
  const pending = (): Promise<void> | undefined => gate ?? current?.catch(() => {});

  /**
   * ⚠️ Must be called on logout. This is app-scoped, not a pinia store, so `resetState` does not
   * reach it — the same reason the orchestrator needs an explicit reset. A read left here belongs
   * to a session that has ended, and the next user would wait on it.
   */
  const reset = (): void => {
    settle();
    current = undefined;
  };

  return { arm, pending, release, reset, track };
});
