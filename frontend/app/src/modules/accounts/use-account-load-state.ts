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
 * How long the gate waits for a read that was promised but never starts.
 *
 * Bounds only the arm-to-{@link UseAccountLoadStateReturn.track} window, which covers everything
 * the session load does before it reaches the accounts. Generous, because expiring early releases
 * a waiter into a store that really is still filling.
 */
const UNSTARTED_READ_TIMEOUT_MS = 30_000;

/**
 * Whether the account store can be trusted to be complete, and a way to wait until it is.
 *
 * @remarks
 * The store fills one chain at a time, so anything snapshotting the account set mid-read sees a
 * partial one and freezes it as its scope. What is handed out is a promise for *timing* only:
 * a caller that needs accounts still reads them itself afterwards.
 *
 * Arming is explicit, and every arm needs a guaranteed {@link UseAccountLoadStateReturn.release}.
 * Tracking only the in-flight read would answer "is a read running?" when consumers are asking
 * "has one happened yet?", and those differ across the whole of session start, where nothing is in
 * flight and the store is empty rather than partial. Blocking on "not started" is also where a
 * deadlock becomes possible: not every session loads accounts, since a resumed one restores
 * balances without re-reading them, so a gate armed by hope waits forever on exactly those.
 */
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
   * The wait is bounded here and only here, because "promised but never started" is the only
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
   * NOT the guarantee — its caller can itself fail to run. The bound is the timer in {@link arm}.
   */
  const release = (): void => {
    settle();
  };

  /**
   * Adopts a read as the one the gate is waiting on.
   *
   * @remarks
   * Clears the unstarted-read timeout, which bounds only the wait for a read that never starts:
   * once one exists, the requests beneath it carry their own timeouts, and expiring mid-read would
   * release waiters into a half-filled store. Settles on rejection too, so a failed read cannot
   * strand a waiter.
   */
  const track = async (load: Promise<void>): Promise<void> => {
    clearTimer();
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
   * Returns `undefined` rather than a resolved promise once accounts are ready, so an idle caller
   * does not even yield a microtask. Awaiting unconditionally reorders everything after it.
   *
   * The rejection is swallowed: a waiter only cares that the read finished, not that it worked.
   */
  const pending = (): Promise<void> | undefined => gate ?? current?.catch(() => {});

  /**
   * Must be called on logout. This is app-scoped, not a pinia store, so `resetState` does not
   * reach it — the same reason the orchestrator needs an explicit reset. A read left here belongs
   * to a session that has ended, and the next user would wait on it.
   */
  const reset = (): void => {
    settle();
    current = undefined;
  };

  return { arm, pending, ready: readonly(ready), release, reset, track };
});
