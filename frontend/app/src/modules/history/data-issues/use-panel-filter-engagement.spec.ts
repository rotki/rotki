import { get, set } from '@vueuse/core';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref, shallowRef } from 'vue';
import { usePanelFilterEngagement } from '@/modules/history/data-issues/use-panel-filter-engagement';

const focused = shallowRef<boolean>(false);

vi.mock('@vueuse/core', async importOriginal => ({
  ...await importOriginal<typeof import('@vueuse/core')>(),
  useFocusWithin: (): { focused: Ref<boolean> } => ({ focused }),
}));

const DISENGAGE_DELAY = 300;

function engagement(): Readonly<Ref<boolean>> {
  return usePanelFilterEngagement(ref<HTMLElement>());
}

describe('usePanelFilterEngagement', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    set(focused, false);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should start disengaged', () => {
    expect(get(engagement())).toBe(false);
  });

  it('should engage as soon as the filter takes focus', async () => {
    const engaged = engagement();

    set(focused, true);
    await vi.advanceTimersByTimeAsync(0);

    expect(get(engaged)).toBe(true);
  });

  it('should stay engaged for the grace period after focus leaves, so a click on a teleported suggestion lands before the drawer dismisses', async () => {
    const engaged = engagement();
    set(focused, true);
    await vi.advanceTimersByTimeAsync(0);

    set(focused, false);
    await vi.advanceTimersByTimeAsync(DISENGAGE_DELAY - 1);

    expect(get(engaged)).toBe(true);
  });

  it('should disengage once the grace period elapses', async () => {
    const engaged = engagement();
    set(focused, true);
    await vi.advanceTimersByTimeAsync(0);

    set(focused, false);
    await vi.advanceTimersByTimeAsync(DISENGAGE_DELAY);

    expect(get(engaged)).toBe(false);
  });

  it('should cancel the pending disengage when focus returns in time', async () => {
    const engaged = engagement();
    set(focused, true);
    await vi.advanceTimersByTimeAsync(0);
    set(focused, false);
    await vi.advanceTimersByTimeAsync(DISENGAGE_DELAY / 2);

    set(focused, true);
    await vi.advanceTimersByTimeAsync(DISENGAGE_DELAY * 2);

    expect(get(engaged)).toBe(true);
  });

  it('should disengage after a full grace period following the last blur', async () => {
    const engaged = engagement();
    set(focused, true);
    await vi.advanceTimersByTimeAsync(0);
    set(focused, false);
    await vi.advanceTimersByTimeAsync(DISENGAGE_DELAY / 2);
    set(focused, true);
    await vi.advanceTimersByTimeAsync(0);

    set(focused, false);
    await vi.advanceTimersByTimeAsync(DISENGAGE_DELAY);

    expect(get(engaged)).toBe(false);
  });
});
