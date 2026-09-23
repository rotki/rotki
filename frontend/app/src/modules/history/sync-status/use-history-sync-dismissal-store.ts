/**
 * The history sync reminder the user set aside this session.
 *
 * @remarks
 * Holds the last-queried timestamp the user dismissed at, so the dismissal lasts until history
 * moves on from it: a sync runs, or a new source brings an older timestamp. It is session state, so
 * the next login that is still out of sync reminds again; the store reset on logout clears it.
 */
export const useHistorySyncDismissalStore = defineStore('history/sync-dismissal', () => {
  const dismissedAt = shallowRef<number>();

  function setDismissedAt(lastQueriedTimestamp: number | undefined): void {
    set(dismissedAt, lastQueriedTimestamp);
  }

  return {
    dismissedAt,
    setDismissedAt,
  };
});
