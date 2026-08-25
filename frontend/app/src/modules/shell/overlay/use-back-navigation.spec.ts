import { beforeEach, describe, expect, it } from 'vitest';
import { createBackNavigationTracker } from './use-back-navigation';

const SEQUENCE_KEY = 'rotkiBackSequence';

/**
 * Stands in for what the browser has already done by the time a guard runs: on a pop the
 * target entry's state is in place, on a push the current entry's state still is.
 *
 * @param sequence - what the tracker stamped there last time it landed, or `undefined` for an
 * entry it has never landed on: a fresh push, or one the browser made on its own.
 * @param position - vue-router's own counter, which only matters where two entries share one.
 */
function atEntry(sequence: number | undefined, position: number = 0): void {
  window.history.replaceState(
    sequence === undefined ? { position } : { [SEQUENCE_KEY]: sequence, position },
    '',
  );
}

function sequenceOf(): number | undefined {
  return window.history.state?.[SEQUENCE_KEY];
}

describe('modules/shell/overlay/use-back-navigation', () => {
  beforeEach(() => {
    atEntry(0);
  });

  it('should not read a push as a back', () => {
    atEntry(3);
    const tracker = createBackNavigationTracker();

    // A push has not written its entry yet when guards run, so the stamp is unchanged.
    expect(tracker.isBack()).toBe(false);
  });

  it('should read an older entry as a back', () => {
    atEntry(3);
    const tracker = createBackNavigationTracker();

    atEntry(2);

    expect(tracker.isBack()).toBe(true);
  });

  it('should not read a forward pop as a back', () => {
    atEntry(3);
    const tracker = createBackNavigationTracker();

    atEntry(4);

    expect(tracker.isBack()).toBe(false);
  });

  it('should stamp an entry it has not landed on before', () => {
    atEntry(3);
    const tracker = createBackNavigationTracker();

    atEntry(undefined);
    tracker.settle(false);

    expect(sequenceOf()).toBe(4);
  });

  it('should leave a revisited entry on the order it already had', () => {
    atEntry(3);
    const tracker = createBackNavigationTracker();

    atEntry(2);
    tracker.settle(false);

    expect(sequenceOf()).toBe(2);
  });

  it('should follow a navigation that landed', () => {
    atEntry(3);
    const tracker = createBackNavigationTracker();

    atEntry(4);
    tracker.settle(false);

    atEntry(3);
    expect(tracker.isBack()).toBe(true);

    tracker.settle(false);
    expect(tracker.isBack()).toBe(false);
  });

  it('should keep reading backs after one was refused, though settle saw the refused entry', () => {
    const current = 3;
    const refusedTarget = 2;
    atEntry(current);
    const tracker = createBackNavigationTracker();

    atEntry(refusedTarget);
    expect(tracker.isBack()).toBe(true);
    tracker.settle(true);
    atEntry(current);

    atEntry(refusedTarget);
    expect(tracker.isBack()).toBe(true);
  });

  it('should read a back between two entries that share one router position', () => {
    const sharedPosition = 3;
    atEntry(1, sharedPosition);
    const tracker = createBackNavigationTracker();

    atEntry(undefined, sharedPosition);
    tracker.settle(false);

    atEntry(1, sharedPosition);
    expect(tracker.isBack()).toBe(true);
  });

  it('should order a push above a forward entry stamped before a reload', () => {
    atEntry(1);
    const trackerAfterReload = createBackNavigationTracker();

    const stampedBeforeReload = 2;
    atEntry(stampedBeforeReload);
    trackerAfterReload.settle(false);

    atEntry(undefined);
    trackerAfterReload.settle(false);

    expect(sequenceOf()).toBe(stampedBeforeReload + 1);
  });

  it('should treat an unstamped entry as neither while the guard runs', () => {
    atEntry(3);
    const tracker = createBackNavigationTracker();

    atEntry(undefined);

    expect(tracker.isBack()).toBe(false);
  });

  it('should start from zero when the first entry carries no stamp', () => {
    atEntry(undefined);
    const tracker = createBackNavigationTracker();

    atEntry(1);

    expect(tracker.isBack()).toBe(false);
  });
});
