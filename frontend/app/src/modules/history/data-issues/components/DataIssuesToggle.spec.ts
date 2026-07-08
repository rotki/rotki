import { mount, type VueWrapper } from '@vue/test-utils';
import { get, set } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, ref } from 'vue';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import DataIssuesToggle from '@/modules/history/data-issues/components/DataIssuesToggle.vue';
import { useDataIssuesInboxStore } from '@/modules/history/data-issues/use-data-issues-inbox-store';
import { PinnedNames } from '@/modules/session/types';
import { createRuiPlugin } from '@/plugins/rui';

const refreshSummary = vi.fn();
const actionableCount = ref<number>(0);
const syncCompleted = ref<number>(0);

vi.mock('@/modules/history/data-issues/use-data-issues-summary', () => ({
  useDataIssuesSummary: (): Record<string, unknown> => ({ actionableCount, refreshSummary }),
}));

vi.mock('@/modules/shell/sync-progress/use-sync-completed', () => ({
  useSyncCompleted: (): Record<string, unknown> => ({ syncCompleted }),
}));

let wrapper: VueWrapper<InstanceType<typeof DataIssuesToggle>> | undefined;

function createWrapper(): VueWrapper<InstanceType<typeof DataIssuesToggle>> {
  wrapper = mount(DataIssuesToggle, {
    global: {
      plugins: [createRuiPlugin({})],
    },
  });
  return wrapper;
}

describe('dataIssuesToggle', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    refreshSummary.mockResolvedValue(undefined);
    set(actionableCount, 0);
    set(syncCompleted, 0);
  });

  afterEach(() => {
    // Unmount so a component's syncCompleted watcher does not survive into the
    // next test and fire on the shared ref.
    wrapper?.unmount();
    wrapper = undefined;
  });

  it('should refresh the summary on mount', () => {
    createWrapper();

    expect(refreshSummary).toHaveBeenCalledOnce();
  });

  it('should open the overlay when toggled while hidden and unpinned', async () => {
    const wrapper = createWrapper();
    const { overlayVisible } = storeToRefs(useDataIssuesInboxStore());

    await wrapper.find('[data-testid="data-issues-toggle"]').trigger('click');

    expect(get(overlayVisible)).toBe(true);
  });

  it('should close the overlay when toggled while already open', async () => {
    const wrapper = createWrapper();
    const { overlayVisible } = storeToRefs(useDataIssuesInboxStore());
    set(overlayVisible, true);

    await wrapper.find('[data-testid="data-issues-toggle"]').trigger('click');

    expect(get(overlayVisible)).toBe(false);
  });

  it('should unpin the panel instead of opening an overlay when it is pinned', async () => {
    const wrapper = createWrapper();
    const { overlayVisible } = storeToRefs(useDataIssuesInboxStore());
    const { pinned } = storeToRefs(useAreaVisibilityStore());
    set(pinned, { name: PinnedNames.DATA_ISSUES, props: {} });

    await wrapper.find('[data-testid="data-issues-toggle"]').trigger('click');

    expect(get(pinned)).toBeNull();
    expect(get(overlayVisible)).toBe(false);
  });

  it('should mark the toggle active when the overlay is open', async () => {
    const wrapper = createWrapper();
    const { overlayVisible } = storeToRefs(useDataIssuesInboxStore());
    const button = wrapper.find('[data-testid="data-issues-toggle"]');
    expect(button.classes()).not.toContain('!bg-rui-primary');

    set(overlayVisible, true);
    await nextTick();

    expect(button.classes()).toContain('!bg-rui-primary');
  });

  it('should mark the toggle active when the panel is pinned', async () => {
    const wrapper = createWrapper();
    const { pinned } = storeToRefs(useAreaVisibilityStore());

    set(pinned, { name: PinnedNames.DATA_ISSUES, props: {} });
    await nextTick();

    expect(wrapper.find('[data-testid="data-issues-toggle"]').classes()).toContain('!bg-rui-primary');
  });

  it('should refresh the summary again when a sync completes', async () => {
    createWrapper();
    expect(refreshSummary).toHaveBeenCalledTimes(1);

    set(syncCompleted, get(syncCompleted) + 1);
    await nextTick();

    expect(refreshSummary).toHaveBeenCalledTimes(2);
  });
});
