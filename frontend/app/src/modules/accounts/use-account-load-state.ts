interface UseAccountLoadStateReturn {
  track: (load: Promise<void>) => Promise<void>;
  pending: () => Promise<void> | undefined;
}

/**
 * When a full account read is in progress, and a way to wait for it.
 *
 * The store is filled one chain at a time, so anything that snapshots the account set while a read
 * is running sees a partial one. The history sync freezes that snapshot as its scope, which silently
 * drops the chains that have not arrived yet.
 *
 * ⚠️ This hands out a promise for *timing*, never for data. A caller that needs accounts must read
 * them itself afterwards.
 */
export const useAccountLoadState = createSharedComposable((): UseAccountLoadStateReturn => {
  let current: Promise<void> | undefined;

  const track = async (load: Promise<void>): Promise<void> => {
    // Settles on rejection too, so a failed read cannot leave a waiter stuck forever.
    const tracked = load.finally(() => {
      if (current === tracked)
        current = undefined;
    });
    current = tracked;
    return tracked;
  };

  /**
   * ⚠️ Returns `undefined` rather than a resolved promise when nothing is running, so an idle
   * caller does not even yield a microtask. Awaiting unconditionally reorders everything after it.
   *
   * The rejection is swallowed: a waiter only cares that the read finished, not that it worked.
   */
  const pending = (): Promise<void> | undefined => current?.catch(() => {});

  return { pending, track };
});
