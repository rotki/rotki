import type { Ref } from 'vue';

/**
 * What caused a piece of table state to change. Replaces the shared `userAction`
 * boolean and the `selfPush` re-entrancy guard: both decisions those flags gated
 * are now pure predicates over the source.
 *
 * - `user`: a direct interaction (sort click, page change, filter edit). The only
 *   source that writes back to the URL.
 * - `route`: deserialized from the URL because the route changed.
 * - `restore`: rehydrated from persisted/saved filters.
 * - `self`: the echo of a URL write we just made. Skips re-deserializing.
 * - `programmatic`: a caller calling `setFilter`/`setPage` without user intent.
 */
export type ChangeSource = 'user' | 'route' | 'restore' | 'self' | 'programmatic';

export interface UseChangeIntentReturn {
  /**
   * Gates the URL write: the *highest-intent* source seen since the last write,
   * not merely the most recent one. `programmatic` never lowers it (see
   * `markSource`). Cleared by a completed write and by the route watcher.
   *
   * Named `pendingIntent` rather than `lastSource` precisely because "last" is
   * what a reader assumes and what silently breaks URL sync: the filter watcher's
   * internal `setPage(1, 'programmatic')` runs before the write and would clobber
   * the user's intent.
   */
  pendingIntent: Ref<ChangeSource>;
  /**
   * Set immediately before we write URL state, consumed by the route watcher so it
   * can tell our own echo from a real navigation. Replaces the `selfPush` boolean,
   * whose correctness depended on a `finally` block winning a race with the watcher.
   */
  pendingUrlSource: Ref<ChangeSource | undefined>;
  markSource: (source: ChangeSource) => void;
  markUserIntent: () => void;
}

/**
 * Owns the provenance of table state changes: which source last earned a URL
 * write, and whether a pending write is our own echo.
 */
export function useChangeIntent(): UseChangeIntentReturn {
  const pendingIntent = ref<ChangeSource>('programmatic');
  const pendingUrlSource = ref<ChangeSource>();

  /**
   * Records the provenance of a state change.
   *
   * `programmatic` means "no user intent". It must not clobber a pending `user`
   * source, otherwise an internal reset (such as the page-1 reset the filter
   * watcher performs) would swallow the URL write the user's change earned.
   * Mirrors the old `if (action) set(userAction, true)`, which likewise only
   * ever raised the flag.
   */
  const markSource = (source: ChangeSource): void => {
    if (source === 'programmatic')
      return;
    set(pendingIntent, source);
  };

  /**
   * Attributes the next state change to the user, so it writes back to the URL.
   *
   * Needed when a consumer owns a ref that feeds a param source: mutating it is a
   * user action, but the table cannot see the interaction. Replaces the old
   * writable `userAction` ref, which any caller could also set back to false.
   */
  const markUserIntent = (): void => {
    set(pendingIntent, 'user');
  };

  return {
    markSource,
    markUserIntent,
    pendingIntent,
    pendingUrlSource,
  };
}
