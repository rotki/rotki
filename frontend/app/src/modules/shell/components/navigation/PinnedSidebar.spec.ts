import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h } from 'vue';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { PinnedNames } from '@/modules/session/types';
import PinnedSidebar from '@/modules/shell/components/navigation/PinnedSidebar.vue';
import { createRuiPlugin } from '@/plugins/rui';

// Replace the registry with two distinct stateful stub components so a tab switch
// can be observed to preserve (or lose) each panel's local state.
vi.mock('@/modules/shell/pinned/pinned-registry', async () => {
  const { defineComponent: dc, h: hh, ref } = await import('vue');
  const { msg } = await import('@/message-key');
  const { PinnedNames: names } = await import('@/modules/session/types');

  const makeStub = (testid: string): ReturnType<typeof dc> => dc({
    setup() {
      const count = ref(0);
      return (): ReturnType<typeof hh> => hh('div', { 'data-testid': testid }, [
        hh('span', { class: 'count' }, String(count.value)),
        hh('button', { class: 'inc', onClick: () => (count.value += 1) }, 'inc'),
      ]);
    },
  });

  return {
    PINNED_PANELS: {
      [names.MATCH_ASSET_MOVEMENTS]: { component: makeStub('stub-match'), icon: 'lu-repeat', labelKey: msg.$t('asset_movement_matching.dialog.title') },
      [names.INTERNAL_TX_CONFLICTS]: { component: makeStub('stub-conflicts'), icon: 'lu-git-merge', labelKey: msg.$t('internal_tx_conflicts.pinned.title') },
    },
  };
});

// Force a desktop breakpoint so the collapsed mini-bar (gated on !isLgAndDown) can render.
vi.mock('@rotki/ui-library', async (importActual) => {
  const actual = await importActual<typeof import('@rotki/ui-library')>();
  const { ref } = await import('vue');
  return {
    ...actual,
    useBreakpoint: (): Record<string, unknown> => ({ isLgAndDown: ref(false), isXlAndDown: ref(false) }),
  };
});

// Render the drawer's default slot inline instead of into a teleport target.
const DrawerStub = defineComponent({
  props: { modelValue: { default: false, type: Boolean } },
  setup: (_, { slots }) => (): ReturnType<typeof h> => h('div', slots.default?.()),
});

function createWrapper(): VueWrapper {
  return mount(PinnedSidebar, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: { RuiNavigationDrawer: DrawerStub },
    },
  });
}

describe('pinnedSidebar', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should render a tab for every pinned panel, including a lone one', async () => {
    const store = useAreaVisibilityStore();
    const wrapper = createWrapper();

    store.pinPanel({ name: PinnedNames.MATCH_ASSET_MOVEMENTS, props: {} });
    await nextTick();
    // The tab strip is the rail's only header, so it shows even for a single panel.
    expect(wrapper.find(`[data-testid="pinned-tab-${PinnedNames.MATCH_ASSET_MOVEMENTS}"]`).exists()).toBe(true);

    store.pinPanel({ name: PinnedNames.INTERNAL_TX_CONFLICTS, props: {} });
    await nextTick();
    expect(wrapper.find(`[data-testid="pinned-tab-${PinnedNames.MATCH_ASSET_MOVEMENTS}"]`).exists()).toBe(true);
    expect(wrapper.find(`[data-testid="pinned-tab-${PinnedNames.INTERNAL_TX_CONFLICTS}"]`).exists()).toBe(true);
  });

  it('should preserve a backgrounded panel state across a tab round-trip', async () => {
    const store = useAreaVisibilityStore();
    const wrapper = createWrapper();

    store.pinPanel({ name: PinnedNames.MATCH_ASSET_MOVEMENTS, props: {} });
    store.pinPanel({ name: PinnedNames.INTERNAL_TX_CONFLICTS, props: {} });
    await nextTick();

    // Focus match and bump its counter.
    store.focusPanel(PinnedNames.MATCH_ASSET_MOVEMENTS);
    await nextTick();
    for (let i = 0; i < 2; i++)
      await wrapper.find('[data-testid="stub-match"] .inc').trigger('click');
    expect(wrapper.find('[data-testid="stub-match"] .count').text()).toBe('2');

    // Switch to conflicts (match backgrounded) then back.
    await wrapper.find(`[data-testid="pinned-tab-${PinnedNames.INTERNAL_TX_CONFLICTS}"]`).trigger('click');
    await nextTick();
    expect(wrapper.find('[data-testid="stub-conflicts"]').exists()).toBe(true);

    await wrapper.find(`[data-testid="pinned-tab-${PinnedNames.MATCH_ASSET_MOVEMENTS}"]`).trigger('click');
    await nextTick();
    expect(wrapper.find('[data-testid="stub-match"] .count').text()).toBe('2');
  });

  it('should remove a tab when its close control is clicked', async () => {
    const store = useAreaVisibilityStore();
    const { pinnedPanels } = storeToRefs(store);
    const wrapper = createWrapper();

    store.pinPanel({ name: PinnedNames.MATCH_ASSET_MOVEMENTS, props: {} });
    store.pinPanel({ name: PinnedNames.INTERNAL_TX_CONFLICTS, props: {} });
    await nextTick();

    await wrapper.find(`[data-testid="pinned-tab-close-${PinnedNames.INTERNAL_TX_CONFLICTS}"]`).trigger('click');
    await nextTick();

    expect(get(pinnedPanels).map(panel => panel.name)).toEqual([PinnedNames.MATCH_ASSET_MOVEMENTS]);
  });

  it('should hide the rail when the last panel is unpinned', async () => {
    const store = useAreaVisibilityStore();
    const { showPinned } = storeToRefs(store);
    createWrapper();

    store.pinPanel({ name: PinnedNames.MATCH_ASSET_MOVEMENTS, props: {} });
    expect(get(showPinned)).toBe(true);

    store.unpinPanel(PinnedNames.MATCH_ASSET_MOVEMENTS);
    expect(get(showPinned)).toBe(false);
  });

  it('should show a collapsed mini-bar and re-expand the rail on click', async () => {
    const store = useAreaVisibilityStore();
    const { showPinned } = storeToRefs(store);
    const wrapper = createWrapper();

    store.pinPanel({ name: PinnedNames.MATCH_ASSET_MOVEMENTS, props: {} });
    set(showPinned, false); // collapse the rail
    await nextTick();

    expect(wrapper.find('[data-testid="pinned-mini-bar"]').exists()).toBe(true);

    await wrapper.find(`[data-testid="pinned-mini-${PinnedNames.MATCH_ASSET_MOVEMENTS}"]`).trigger('click');

    expect(get(showPinned)).toBe(true);
  });
});
