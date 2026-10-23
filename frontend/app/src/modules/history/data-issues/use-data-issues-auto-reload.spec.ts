import { mount } from '@vue/test-utils';
import { set } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, nextTick, ref } from 'vue';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';
import { useDataIssuesAutoReload } from '@/modules/history/data-issues/use-data-issues-auto-reload';

const syncCompleted = ref<boolean>(false);

vi.mock('@/modules/shell/sync-progress/use-sync-completed', () => ({
  useSyncCompleted: (): Record<string, unknown> => ({ syncCompleted }),
}));

function mountView(reload: () => Promise<void>): void {
  mount(defineComponent({
    setup() {
      useDataIssuesAutoReload(reload);
      return (): unknown => h('div');
    },
  }));
}

describe('useDataIssuesAutoReload', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    set(syncCompleted, false);
  });

  it('should reload when a sync completes', async () => {
    const reload = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
    mountView(reload);

    set(syncCompleted, true);
    await nextTick();

    expect(reload).toHaveBeenCalledOnce();
  });

  it('should reload when historical balance processing completes', async () => {
    const reload = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
    mountView(reload);

    useHistoricalBalanceProcessingStore().notifyHistoricalBalanceProcessingCompleted();
    await nextTick();

    expect(reload).toHaveBeenCalledOnce();
  });

  it('should reload when current balance detection completes', async () => {
    const reload = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
    mountView(reload);

    useHistoricalBalanceProcessingStore().notifyCurrentBalanceDetectionCompleted();
    await nextTick();

    expect(reload).toHaveBeenCalledOnce();
  });
});
