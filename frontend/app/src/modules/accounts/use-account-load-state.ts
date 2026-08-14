import type { Ref } from 'vue';
import { logger } from '@/modules/core/common/logging/logging';

interface UseAccountLoadStateReturn {
  arm: () => void;
  release: () => void;
  track: (load: Promise<void>) => Promise<void>;
  pending: () => Promise<void> | undefined;
  /** The same answer as {@link pending}, for a consumer that renders it rather than awaits it. */
  ready: Readonly<Ref<boolean>>;
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
/**
 * How long the gate will wait for a read that has been promised but never starts.
 *
 * Bounds only the arm→`track` window — everything the session load does before it reaches the
 * accounts (the ignored/whitelisted lists, then the exchange rates). Generous for that stretch,
 * because expiring early is not free: it releases a waiter into a store that really is still
 * filling, which is the bug this composable exists to prevent.
 */
const UNSTARTED_READ_TIMEOUT_MS = 30_000;

export const useAccountLoadState = createSharedComposable((): UseAccountLoadStateReturn => {
  let current: Promise<void> | undefined;
  let gate: Promise<void> | undefined;
  let openGate: (() => void) | undefined;
  let unstarted: ReturnType<typeof setTimeout> | undefined;

  // Starts open, for the same reason `pending()` returns undefined when nothing is armed: a
  // session that never promised a read has nothing to wait for. Only `arm` closes it.
  const ready = ref<boolean>(true);

  const clearTimer = (): void => {
    if (unstarted === undefined)
      return;

    clearTimeout(unstarted);
    unstarted = undefined;
  };

  /**
   * Resolves the gate rather than dropping it: a waiter holds the promise itself, so replacing the
   * reference without resolving it would strand that waiter for the life of the process.
   */
  const settle = (): void => {
    clearTimer();
    openGate?.();
    gate = undefined;
    openGate = undefined;
    set(ready, true);
  };

  /**
   * Declares that a full read is coming, before the first `await` on the way to it. Idempotent, so
   * a second caller joins the existing gate instead of replacing one that already has waiters.
   *
   * 🔴 The wait is bounded here and only here, because "promised but never started" is the only
   * state that can hang forever. Once {@link track} holds a real promise the wait is safe to leave
   * open: that promise settles on rejection too, and every request under it carries its own
   * timeout. An unstarted read has no such guarantee — `release()` is normally what ends it, but
   * its caller sits behind `allSettled([fetchCached(), …])`, and `allSettled` cannot settle if
   * `fetchCached` never does. That is not hypothetical: a poisoned `prices:exchange-rates` id
   * stalled `fetchCached` on its first await, and without this the history sync waited forever.
   */
  const arm = (): void => {
    if (gate)
      return;

    set(ready, false);
    gate = new Promise<void>((resolve) => {
      openGate = resolve;
    });
    unstarted = setTimeout(() => {
      logger.warn(
        `Accounts were not read within ${UNSTARTED_READ_TIMEOUT_MS}ms of the session load starting. `
        + 'Releasing readiness: consumers proceed against whatever the store holds, which may be incomplete.',
      );
      settle();
    }, UNSTARTED_READ_TIMEOUT_MS);
  };

  /**
   * Ends the wait without a read having happened. The counterpart to {@link arm} for the paths that
   * turn out not to load accounts.
   *
   * ⚠️ NOT the guarantee — its caller can itself fail to run. The bound is the timer in {@link arm}.
   */
  const release = (): void => {
    settle();
  };

  const track = async (load: Promise<void>): Promise<void> => {
    // A real read exists now, so the unstarted-read bound no longer applies: this promise settles
    // on rejection too, and the requests under it carry their own timeouts. Expiring mid-read would
    // release waiters into a half-filled store, which is exactly what the gate is for.
    clearTimer();
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

  return { arm, pending, ready: readonly(ready), release, reset, track };
});
