import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { get } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { nextTick } from 'vue';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import BalanceDivergenceToggle from '@/modules/history/balances/BalanceDivergenceToggle.vue';
import { PinnedNames } from '@/modules/session/types';
import { createRuiPlugin } from '@/plugins/rui';

function createWrapper(): VueWrapper<InstanceType<typeof BalanceDivergenceToggle>> {
  return mount(BalanceDivergenceToggle, {
    global: {
      plugins: [createRuiPlugin({})],
    },
  });
}

describe('balanceDivergenceToggle', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should pin the panel when toggled while unpinned', async () => {
    const wrapper = createWrapper();
    const { pinnedPanels } = storeToRefs(useAreaVisibilityStore());

    await wrapper.find('[data-testid="balance-divergence-toggle"]').trigger('click');

    expect(get(pinnedPanels).map(panel => panel.name)).toContain(PinnedNames.BALANCE_DIVERGENCE);
  });

  it('should unpin the panel when toggled while shown and active', async () => {
    const wrapper = createWrapper();
    const visibility = useAreaVisibilityStore();
    const { pinnedPanels } = storeToRefs(visibility);
    visibility.pinPanel({ name: PinnedNames.BALANCE_DIVERGENCE, props: {} });

    await wrapper.find('[data-testid="balance-divergence-toggle"]').trigger('click');

    expect(get(pinnedPanels)).toHaveLength(0);
  });

  it('should switch a panel pinned on a data issue to the manual search form', async () => {
    const wrapper = createWrapper();
    const visibility = useAreaVisibilityStore();
    const { pinnedPanels } = storeToRefs(visibility);
    visibility.pinPanel({ name: PinnedNames.BALANCE_DIVERGENCE, props: { issue: createMock<DataIssue>({ id: 1 }) } });

    await wrapper.find('[data-testid="balance-divergence-toggle"]').trigger('click');

    expect(get(pinnedPanels)).toEqual([{ name: PinnedNames.BALANCE_DIVERGENCE, props: {} }]);
  });

  it('should mark the toggle active when the panel is pinned', async () => {
    const wrapper = createWrapper();
    const visibility = useAreaVisibilityStore();
    const button = wrapper.find('[data-testid="balance-divergence-toggle"]');
    expect(button.classes()).not.toContain('!bg-rui-primary');

    visibility.pinPanel({ name: PinnedNames.BALANCE_DIVERGENCE, props: {} });
    await nextTick();

    expect(button.classes()).toContain('!bg-rui-primary');
  });
});
