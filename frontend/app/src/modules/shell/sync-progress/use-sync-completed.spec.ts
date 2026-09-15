import { get, set } from '@vueuse/core';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, type Ref, ref } from 'vue';

const isSettled = ref<boolean>(false);

vi.mock('@/modules/history/events/tx/use-sync-rollup', () => ({
  useSyncRollup: (): Record<string, unknown> => ({ isSettled }),
}));

/**
 * Imports a fresh copy of the shared composable. `createSharedComposable` caches
 * its instance for the module's lifetime, so each test resets modules to get an
 * isolated counter and watcher.
 */
async function freshUseSyncCompleted(): Promise<() => { syncCompleted: Ref<number> }> {
  vi.resetModules();
  const mod = await import('@/modules/shell/sync-progress/use-sync-completed');
  return mod.useSyncCompleted;
}

describe('useSyncCompleted', () => {
  beforeEach(() => {
    set(isSettled, false);
  });

  it('should start the completion counter at zero', async () => {
    const useSyncCompleted = await freshUseSyncCompleted();
    const { syncCompleted } = useSyncCompleted();

    expect(get(syncCompleted)).toBe(0);
  });

  it('should bump the counter when the refresh settles', async () => {
    const useSyncCompleted = await freshUseSyncCompleted();
    const { syncCompleted } = useSyncCompleted();

    set(isSettled, true);
    await nextTick();

    expect(get(syncCompleted)).toBe(1);
  });

  it('should not bump the counter when a settled refresh starts working again', async () => {
    set(isSettled, true);
    const useSyncCompleted = await freshUseSyncCompleted();
    const { syncCompleted } = useSyncCompleted();

    set(isSettled, false);
    await nextTick();

    expect(get(syncCompleted)).toBe(0);
  });

  it('should bump once per transition into settled', async () => {
    const useSyncCompleted = await freshUseSyncCompleted();
    const { syncCompleted } = useSyncCompleted();

    set(isSettled, true);
    await nextTick();
    set(isSettled, false);
    await nextTick();
    set(isSettled, true);
    await nextTick();

    expect(get(syncCompleted)).toBe(2);
  });
});
