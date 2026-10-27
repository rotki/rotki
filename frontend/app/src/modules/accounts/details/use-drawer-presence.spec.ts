import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { DRAWER_SLIDE_MS, useDrawerPresence } from '@/modules/accounts/details/use-drawer-presence';

describe('useDrawerPresence', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should show the open item at once and mark it ready only once the slide in is over', async () => {
    const current = ref<string>();
    const { ready, shown } = useDrawerPresence(current);

    set(current, 'a');
    await nextTick();

    expect(get(shown)).toBe('a');
    expect(get(ready)).toBe(false);

    vi.advanceTimersByTime(DRAWER_SLIDE_MS - 1);
    expect(get(ready)).toBe(false);

    vi.advanceTimersByTime(1);
    expect(get(ready)).toBe(true);
  });

  it('should keep showing the item while the drawer slides out, and drop it when the slide is over', async () => {
    const current = ref<string>('a');
    const { onClosed, ready, shown } = useDrawerPresence(current);
    vi.advanceTimersByTime(DRAWER_SLIDE_MS);

    set(current, undefined);
    await nextTick();

    expect(get(shown)).toBe('a');
    expect(get(ready)).toBe(true);

    onClosed();

    expect(get(shown)).toBeUndefined();
    expect(get(ready)).toBe(false);
  });

  it('should switch to another item at once, without waiting for a slide', async () => {
    const current = ref<string>('a');
    const { ready, shown } = useDrawerPresence(current);
    vi.advanceTimersByTime(DRAWER_SLIDE_MS);

    set(current, 'b');
    await nextTick();

    expect(get(shown)).toBe('b');
    expect(get(ready)).toBe(true);
  });

  it('should keep the content when the drawer reopens before its slide out ended', async () => {
    const current = ref<string>('a');
    const { onClosed, ready, shown } = useDrawerPresence(current);
    vi.advanceTimersByTime(DRAWER_SLIDE_MS);

    set(current, undefined);
    await nextTick();
    set(current, 'a');
    await nextTick();
    onClosed();

    expect(get(shown)).toBe('a');
    expect(get(ready)).toBe(true);
  });

  it('should not turn ready after a drawer that closed before its slide in was over', async () => {
    const current = ref<string>();
    const { onClosed, ready } = useDrawerPresence(current);

    set(current, 'a');
    await nextTick();
    set(current, undefined);
    await nextTick();
    onClosed();
    vi.advanceTimersByTime(DRAWER_SLIDE_MS);

    expect(get(ready)).toBe(false);
  });
});
