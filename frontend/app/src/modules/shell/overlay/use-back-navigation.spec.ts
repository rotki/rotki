import { beforeEach, describe, expect, it } from 'vitest';
import { createBackNavigationTracker } from './use-back-navigation';

/**
 * Stands in for what the browser has already done by the time a guard runs: on a pop the
 * target entry's state is in place, on a push the current entry's state still is.
 */
function atEntry(position: number | undefined): void {
  window.history.replaceState(position === undefined ? {} : { position }, '');
}

describe('modules/shell/overlay/use-back-navigation', () => {
  beforeEach(() => {
    atEntry(0);
  });

  it('should not read a push as a back', () => {
    atEntry(3);
    const tracker = createBackNavigationTracker();

    // A push has not written its entry yet when guards run, so the position is unchanged.
    expect(tracker.isBack()).toBe(false);
  });

  it('should read a lower position as a back', () => {
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

  it('should keep reading backs after one was refused', () => {
    atEntry(3);
    const tracker = createBackNavigationTracker();

    // First back, refused by the guard. vue-router restores the entry only after the hook
    // has run, so `settle` sees the position it was moving to, not the one it stayed on.
    atEntry(2);
    expect(tracker.isBack()).toBe(true);
    tracker.settle(true);
    atEntry(3);

    // Second back with another layer still open: recording the refused position would have
    // made this compare 2 < 2 and slip through as a push.
    atEntry(2);
    expect(tracker.isBack()).toBe(true);
  });

  it('should treat an entry with no position as neither', () => {
    atEntry(3);
    const tracker = createBackNavigationTracker();

    atEntry(undefined);

    expect(tracker.isBack()).toBe(false);
  });

  it('should start from zero when the first entry carries no position', () => {
    atEntry(undefined);
    const tracker = createBackNavigationTracker();

    atEntry(1);

    expect(tracker.isBack()).toBe(false);
  });
});
