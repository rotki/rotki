import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { nextTick } from 'vue';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { PinnedNames } from '@/modules/session/types';
import PinnedIndicator from '@/modules/shell/components/navigation/PinnedIndicator.vue';
import { createRuiPlugin } from '@/plugins/rui';

let wrapper: VueWrapper<InstanceType<typeof PinnedIndicator>> | undefined;

function createWrapper(): VueWrapper<InstanceType<typeof PinnedIndicator>> {
  wrapper = mount(PinnedIndicator, {
    attachTo: document.body,
    global: { plugins: [createRuiPlugin({})] },
    props: { visible: false },
  });
  return wrapper;
}

describe('pinnedIndicator', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = '';
  });

  it('should render nothing when no panel is pinned', () => {
    const wrapper = createWrapper();
    expect(wrapper.find('[data-testid="pinned-indicator"]').exists()).toBe(false);
  });

  it('should toggle rail visibility when a single panel is pinned', async () => {
    const store = useAreaVisibilityStore();
    store.pinPanel({ name: PinnedNames.DATA_ISSUES, props: {} });
    const wrapper = createWrapper();
    await nextTick();

    await wrapper.find('[data-testid="pinned-indicator"]').trigger('click');

    expect(wrapper.emitted('update:visible')?.at(-1)).toEqual([true]);
  });

  it('should show the pinned count and still toggle the rail when several are pinned', async () => {
    const store = useAreaVisibilityStore();
    store.pinPanel({ name: PinnedNames.MATCH_ASSET_MOVEMENTS, props: {} });
    store.pinPanel({ name: PinnedNames.INTERNAL_TX_CONFLICTS, props: {} });
    const wrapper = mount(PinnedIndicator, {
      attachTo: document.body,
      global: { plugins: [createRuiPlugin({})] },
      props: { visible: true },
    });
    await nextTick();

    // The badge shows the count, and clicking still collapses an open rail.
    expect(wrapper.text()).toContain('2');
    await wrapper.find('[data-testid="pinned-indicator"]').trigger('click');
    expect(wrapper.emitted('update:visible')?.at(-1)).toEqual([false]);

    wrapper.unmount();
  });
});
