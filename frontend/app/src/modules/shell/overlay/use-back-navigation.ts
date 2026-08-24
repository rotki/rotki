/**
 * Reads the position vue-router stamps on every history entry. Absent on the very first
 * load, before the router has replaced the initial entry with one of its own.
 */
function readPosition(): number | undefined {
  const position: unknown = window.history.state?.position;
  return typeof position === 'number' ? position : undefined;
}

export interface BackNavigationTracker {
  /**
   * Whether the navigation now starting is a back gesture rather than a push. Only
   * meaningful from inside a `beforeEach` guard.
   */
  isBack: () => boolean;
  /**
   * Records the outcome of a navigation. Call from `afterEach`, passing whether the hook
   * was handed a failure.
   */
  settle: (failed: boolean) => void;
}

/**
 * Tells a back gesture from a push, which vue-router reports to its own history listener
 * but not to a guard.
 *
 * The signal is the entry position: on a pop the browser has already swapped
 * `history.state` in by the time guards run, so the position read there is the entry being
 * moved to, while a push does not write its entry until after the guards have passed. A
 * position lower than the one the app is showing therefore means back.
 */
export function createBackNavigationTracker(): BackNavigationTracker {
  let currentPosition = readPosition() ?? 0;

  return {
    isBack(): boolean {
      const target = readPosition();
      return target !== undefined && target < currentPosition;
    },
    settle(failed: boolean): void {
      // Only a navigation that landed moves the position. vue-router restores an aborted
      // pop asynchronously, after this hook, so reading the position here would record the
      // entry the guard just refused to move to. The next back would then compare against
      // that lower number and not read as a back at all, which let the second of two
      // stacked overlays fall through and leave the page.
      if (failed)
        return;

      currentPosition = readPosition() ?? 0;
    },
  };
}
