import { get, set } from '@vueuse/core';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, type Ref, ref } from 'vue';
import { SyncPhase } from '@/modules/shell/sync-progress/types';

const phase = ref<SyncPhase>(SyncPhase.IDLE);

vi.mock('@/modules/shell/sync-progress/use-sync-progress', () => ({
  useSyncProgress: (): Record<string, unknown> => ({ phase }),
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
    set(phase, SyncPhase.IDLE);
  });

  it('should start the completion counter at zero', async () => {
    const useSyncCompleted = await freshUseSyncCompleted();
    const { syncCompleted } = useSyncCompleted();

    expect(get(syncCompleted)).toBe(0);
  });

  it('should bump the counter when the sync phase reaches complete', async () => {
    const useSyncCompleted = await freshUseSyncCompleted();
    const { syncCompleted } = useSyncCompleted();

    set(phase, SyncPhase.COMPLETE);
    await nextTick();

    expect(get(syncCompleted)).toBe(1);
  });

  it('should not bump the counter for non-complete phase transitions', async () => {
    const useSyncCompleted = await freshUseSyncCompleted();
    const { syncCompleted } = useSyncCompleted();

    set(phase, SyncPhase.SYNCING);
    await nextTick();

    expect(get(syncCompleted)).toBe(0);
  });

  it('should bump once per transition into complete', async () => {
    const useSyncCompleted = await freshUseSyncCompleted();
    const { syncCompleted } = useSyncCompleted();

    set(phase, SyncPhase.COMPLETE);
    await nextTick();
    set(phase, SyncPhase.SYNCING);
    await nextTick();
    set(phase, SyncPhase.COMPLETE);
    await nextTick();

    expect(get(syncCompleted)).toBe(2);
  });
});
