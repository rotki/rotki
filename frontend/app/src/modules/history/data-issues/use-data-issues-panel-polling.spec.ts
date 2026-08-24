import { mount } from '@vue/test-utils';
import { set } from '@vueuse/core';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, KeepAlive, type Ref, ref, shallowRef } from 'vue';
import { useDataIssuesPanelPolling } from '@/modules/history/data-issues/use-data-issues-panel-polling';

const syncCompleted = ref<boolean>(false);

vi.mock('@/modules/shell/sync-progress/use-sync-completed', () => ({
  useSyncCompleted: (): Record<string, unknown> => ({ syncCompleted }),
}));

const POLL_INTERVAL = 10_000;

/**
 * Mounts the composable inside a `<KeepAlive>` so it is deactivated rather than
 * unmounted when hidden, which is how the panel actually behaves.
 */
function mountPanel(hasRemediatingRows: Ref<boolean>, reload: () => Promise<void>): {
  show: (visible: boolean) => Promise<void>;
  unmount: () => void;
} {
  const Panel = defineComponent({
    name: 'Panel',
    setup() {
      useDataIssuesPanelPolling(hasRemediatingRows, reload);
      return (): unknown => h('div');
    },
  });

  const visible = shallowRef<boolean>(true);
  const wrapper = mount(defineComponent({
    setup() {
      return (): unknown => h(KeepAlive, null, [visible.value ? h(Panel) : null]);
    },
  }));

  return {
    show: async (next: boolean): Promise<void> => {
      set(visible, next);
      await wrapper.vm.$nextTick();
    },
    unmount: (): void => {
      wrapper.unmount();
    },
  };
}

describe('useDataIssuesPanelPolling', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    set(syncCompleted, false);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should not poll while nothing is auto-remediating', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    const panel = mountPanel(ref(false), reload);

    await vi.advanceTimersByTimeAsync(POLL_INTERVAL * 3);

    expect(reload).not.toHaveBeenCalled();
    panel.unmount();
  });

  it('should poll once a row starts auto-remediating', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    const remediating = ref<boolean>(false);
    const panel = mountPanel(remediating, reload);

    set(remediating, true);
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL * 2);

    expect(reload).toHaveBeenCalledTimes(2);
    panel.unmount();
  });

  it('should stop polling when the last remediating row settles', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    const remediating = ref<boolean>(true);
    const panel = mountPanel(remediating, reload);
    set(remediating, false);
    await vi.advanceTimersByTimeAsync(0);
    reload.mockClear();

    await vi.advanceTimersByTimeAsync(POLL_INTERVAL * 3);

    expect(reload).not.toHaveBeenCalled();
    panel.unmount();
  });

  it('should stop polling while hidden, so a backgrounded panel makes no requests', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    const remediating = ref<boolean>(true);
    const panel = mountPanel(remediating, reload);
    await vi.advanceTimersByTimeAsync(0);

    await panel.show(false);
    reload.mockClear();
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL * 3);

    expect(reload).not.toHaveBeenCalled();
    panel.unmount();
  });

  // Under <KeepAlive> the panel's reactivity stays live while hidden, so a row that
  // starts remediating in the background still fires the watcher. Without the
  // activation gate that would restart the poll on a panel nobody is looking at.
  it('should not start polling for a row that begins remediating while hidden', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    const remediating = ref<boolean>(false);
    const panel = mountPanel(remediating, reload);
    await panel.show(false);

    set(remediating, true);
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL * 3);

    expect(reload).not.toHaveBeenCalled();
    panel.unmount();
  });

  it('should resume polling when shown again with rows still remediating', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    const remediating = ref<boolean>(true);
    const panel = mountPanel(remediating, reload);
    await panel.show(false);
    reload.mockClear();

    await panel.show(true);
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL);

    expect(reload).toHaveBeenCalled();
    panel.unmount();
  });

  it('should reload when a sync completes while visible', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    const panel = mountPanel(ref(false), reload);

    set(syncCompleted, true);
    await vi.advanceTimersByTimeAsync(0);

    expect(reload).toHaveBeenCalledOnce();
    panel.unmount();
  });

  it('should defer a sync that completes while hidden instead of dropping it', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    const panel = mountPanel(ref(false), reload);
    await panel.show(false);

    set(syncCompleted, true);
    await vi.advanceTimersByTimeAsync(0);

    expect(reload).not.toHaveBeenCalled();
    panel.unmount();
  });

  it('should catch up a deferred sync refresh once shown again', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    const panel = mountPanel(ref(false), reload);
    await panel.show(false);
    set(syncCompleted, true);
    await vi.advanceTimersByTimeAsync(0);

    await panel.show(true);
    await vi.advanceTimersByTimeAsync(0);

    expect(reload).toHaveBeenCalledOnce();
    panel.unmount();
  });

  it('should catch up only once, not on every later activation', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    const panel = mountPanel(ref(false), reload);
    await panel.show(false);
    set(syncCompleted, true);
    await vi.advanceTimersByTimeAsync(0);
    await panel.show(true);
    await vi.advanceTimersByTimeAsync(0);
    reload.mockClear();

    await panel.show(false);
    await panel.show(true);
    await vi.advanceTimersByTimeAsync(0);

    expect(reload).not.toHaveBeenCalled();
    panel.unmount();
  });
});
