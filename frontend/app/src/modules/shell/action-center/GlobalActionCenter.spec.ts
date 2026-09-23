import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import MissingPricesDialog from '@/modules/assets/prices/missing/MissingPricesDialog.vue';
import { useMissingPricesDialog } from '@/modules/assets/prices/missing/use-missing-prices-dialog';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { PinnedNames, toPinned } from '@/modules/session/types';
import { SettingsCategoryIds } from '@/modules/settings/setting-highlight-ids';
import { useSettingsHighlight } from '@/modules/settings/use-settings-highlight';
import GlobalActionCenter from '@/modules/shell/action-center/GlobalActionCenter.vue';

const { openUrl } = vi.hoisted(() => ({ openUrl: vi.fn<(url: string) => Promise<void>>() }));

const state = {
  markSeen: vi.fn<() => void>(),
  push: vi.fn<(to: unknown) => Promise<void>>(),
  refreshAll: vi.fn<() => Promise<void>>(),
};

vi.mock('@/modules/assets/prices/missing/use-missing-prices', () => ({
  useMissingPrices: (): object => ({ missingPriceIdentifiers: computed(() => ['ETH']) }),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): object => ({ openUrl }),
}));

vi.mock('@/modules/shell/action-center/use-global-action-center', () => ({
  useGlobalActionCenter: (): object => ({
    checking: computed(() => false),
    cleared: computed(() => []),
    count: computed(() => 2),
    markSeen: state.markSeen,
    newCount: computed(() => 1),
    newIds: computed(() => ['missing-prices']),
    refreshAll: state.refreshAll,
    refreshing: computed(() => false),
    sections: computed(() => []),
  }),
}));

vi.mock('vue-router', () => ({
  useRouter: (): object => ({ push: state.push }),
}));

function mountCenter(): VueWrapper<InstanceType<typeof GlobalActionCenter>> {
  return mount(GlobalActionCenter, { attachTo: document.body });
}

/** Opens the menu through its v-model and resolves with the teleported list once it lands. */
async function openMenu(wrapper: VueWrapper<InstanceType<typeof GlobalActionCenter>>): Promise<VueWrapper> {
  wrapper.findComponent({ name: 'RuiMenu' }).vm.$emit('update:modelValue', true);
  await flushPromises();
  return vi.waitFor(() => {
    const list = wrapper.findComponent({ name: 'ActionCenterList' });
    expect(list.exists()).toBe(true);
    return list;
  });
}

describe('modules/shell/action-center/GlobalActionCenter', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    vi.clearAllMocks();
    openUrl.mockResolvedValue();
    state.push.mockResolvedValue();
    state.refreshAll.mockResolvedValue();
  });

  it('should be the trigger that carries the badge, numbering only what is new', () => {
    const wrapper = mountCenter();
    const badge = wrapper.findComponent({ name: 'RuiBadge' });

    expect(badge.props('modelValue')).toBe(true);
    expect(badge.props('text')).toBe('1');
  });

  it('should hand the new rows to the panel so it can mark them', async () => {
    const wrapper = mountCenter();
    const list = await openMenu(wrapper);

    expect(list.props()).toMatchObject({ newIds: ['missing-prices'] });
  });

  it('should record what was seen when the menu closes, not when it opens', async () => {
    const wrapper = mountCenter();
    await openMenu(wrapper);
    expect(state.markSeen).not.toHaveBeenCalled();

    wrapper.findComponent({ name: 'RuiMenu' }).vm.$emit('update:modelValue', false);
    await nextTick();

    expect(state.markSeen).toHaveBeenCalledOnce();
  });

  it('should navigate on a route target and close the menu', async () => {
    const wrapper = mountCenter();
    const list = await openMenu(wrapper);

    list.vm.$emit('open', { kind: 'route', to: { name: '/asset-manager/more/missing-mappings/' } });
    await nextTick();

    expect(state.push).toHaveBeenCalledWith({ name: '/asset-manager/more/missing-mappings/' });
    expect(wrapper.findComponent({ name: 'RuiMenu' }).props('modelValue')).toBe(false);
  });

  it('should ask the settings page to bring a highlighted entry into view before navigating there', async () => {
    const { clearHighlight, highlightTarget } = useSettingsHighlight();
    clearHighlight();
    const wrapper = mountCenter();
    const list = await openMenu(wrapper);

    list.vm.$emit('open', { highlight: SettingsCategoryIds.INDEXER, kind: 'route', to: { name: '/settings/chains/' } });
    await nextTick();

    expect(get(highlightTarget)).toEqual({ categoryId: SettingsCategoryIds.INDEXER, highlightId: undefined });
    expect(state.push).toHaveBeenCalledWith({ name: '/settings/chains/' });
  });

  it('should open a pin target in the pinned rail without navigating', async () => {
    const store = useAreaVisibilityStore();
    const wrapper = mountCenter();
    const list = await openMenu(wrapper);

    list.vm.$emit('open', { kind: 'pin', panel: toPinned(PinnedNames.DATA_ISSUES, {}) });
    await nextTick();

    expect(get(store.activePinnedId)).toBe(PinnedNames.DATA_ISSUES);
    expect(state.push).not.toHaveBeenCalled();
  });

  it('should run a run target in place, leaving the menu open to show the outcome', async () => {
    const run = vi.fn<() => void>();
    const wrapper = mountCenter();
    const list = await openMenu(wrapper);

    list.vm.$emit('open', { kind: 'run', run });
    await nextTick();

    expect(run).toHaveBeenCalledOnce();
    expect(wrapper.findComponent({ name: 'RuiMenu' }).props('modelValue')).toBe(true);
  });

  it('should close the menu for a run target that opens a surface of its own', async () => {
    const run = vi.fn<() => void>();
    const wrapper = mountCenter();
    const list = await openMenu(wrapper);

    list.vm.$emit('open', { closesCenter: true, kind: 'run', run });
    await nextTick();

    expect(run).toHaveBeenCalledOnce();
    expect(wrapper.findComponent({ name: 'RuiMenu' }).props('modelValue')).toBe(false);
  });

  it('should mount the missing prices dialog with the missing assets only once it is opened', async () => {
    const wrapper = mountCenter();
    expect(wrapper.findComponent(MissingPricesDialog).exists()).toBe(false);

    useMissingPricesDialog().show();
    await nextTick();

    const dialog = wrapper.findComponent(MissingPricesDialog);
    expect(dialog.props('identifiers')).toEqual(['ETH']);
    expect(dialog.props('open')).toBe(true);
  });

  it('should open an external target outside the app and close the menu', async () => {
    const wrapper = mountCenter();
    const list = await openMenu(wrapper);

    list.vm.$emit('open', { kind: 'external', url: 'https://docs.rotki.com' });
    await nextTick();

    expect(openUrl).toHaveBeenCalledWith('https://docs.rotki.com');
    expect(state.push).not.toHaveBeenCalled();
    expect(wrapper.findComponent({ name: 'RuiMenu' }).props('modelValue')).toBe(false);
  });

  it('should re-scan when asked from the panel', async () => {
    const wrapper = mountCenter();
    const list = await openMenu(wrapper);

    list.vm.$emit('refresh');

    expect(state.refreshAll).toHaveBeenCalledOnce();
  });
});
