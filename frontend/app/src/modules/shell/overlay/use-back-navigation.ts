/** Key the tracker stamps its own entry ordering under. */
const SEQUENCE_KEY = 'rotkiBackSequence';

function readSequence(): number | undefined {
  const state: unknown = window.history.state;
  const sequence: unknown = typeof state === 'object' && state !== null
    ? Reflect.get(state, SEQUENCE_KEY)
    : undefined;
  return typeof sequence === 'number' ? sequence : undefined;
}

function stamp(sequence: number): void {
  window.history.replaceState({ ...window.history.state, [SEQUENCE_KEY]: sequence }, '');
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
 * The signal is an ordering stamped on every entry the tracker lands on. On a pop the
 * browser has already swapped `history.state` in by the time guards run, so what is read
 * there belongs to the entry being moved to, while a push does not write its entry until
 * after the guards have passed. An older stamp therefore means back.
 *
 * The stamp is the tracker's own rather than vue-router's `position` because a position is
 * not always newer on a newer entry: an entry the browser created on its own carries no
 * state, and the router replaces it with the position it was already on, leaving two
 * adjacent entries comparing equal. An unstamped entry is by definition one not landed on
 * before, so it is always stamped newer, which is the distinction the position loses.
 */
export function createBackNavigationTracker(): BackNavigationTracker {
  let issued = readSequence() ?? 0;
  let currentSequence = issued;

  return {
    isBack(): boolean {
      const target = readSequence();
      return target !== undefined && target < currentSequence;
    },
    settle(failed: boolean): void {
      // vue-router restores an aborted pop after this hook, so the entry readable here is
      // the one the guard refused to move to. Recording it would leave the next back
      // comparing against that older stamp and reading as a push.
      if (failed)
        return;

      // A stamped entry is being revisited and keeps its order; restamping it would make
      // every later back look like a push. Its stamp still raises the high-water mark;
      // otherwise a reload landing behind entries the previous tracker stamped would hand
      // their numbers out a second time.
      const landed = readSequence();
      if (landed !== undefined) {
        currentSequence = landed;
        issued = Math.max(issued, landed);
        return;
      }

      currentSequence = ++issued;
      stamp(currentSequence);
    },
  };
}
