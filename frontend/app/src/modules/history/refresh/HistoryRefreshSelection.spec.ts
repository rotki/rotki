import type { ChainAddress } from '@/modules/history/events/event-payloads';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type Component, defineComponent, h, nextTick, type VNode } from 'vue';
import HistoryRefreshSelection from '@/modules/history/refresh/HistoryRefreshSelection.vue';

/**
 * The seam: this component is wiring. It owns the menu's open state, hands the shared selection
 * down to whichever tab is showing, routes "select all" to that tab's own toggle, and emits the
 * active tab's picks as the refresh payload before clearing and closing.
 *
 * What each tab does with its picks belongs to the tab components, and the selection state itself
 * is covered by `use-history-refresh-selection.spec.ts`.
 */

// RuiMenu teleports its content lazily; stub it so the activator and the panel are both in the
// tree without opening it, while still recording the open state the component drives.
const RuiMenuStub = defineComponent({
  name: 'RuiMenu',
  props: { modelValue: { default: false, type: Boolean } },
  emits: ['update:modelValue'],
  template: '<div><slot name="activator" :attrs="{}" /><slot /></div>',
});

const toggles = {
  chains: vi.fn(),
  events: vi.fn(),
  exchanges: vi.fn(),
  protocols: vi.fn(),
};

function tabStub(name: string, toggleSelectAll: () => void): Component {
  return defineComponent({
    name,
    props: {
      chain: { default: undefined, type: String },
      modelValue: { default: () => [], type: Array },
      processing: { default: false, type: Boolean },
      search: { default: '', type: String },
    },
    emits: ['update:modelValue', 'update:search', 'update:chain', 'update:all-selected'],
    setup(_, { expose }): () => VNode {
      expose({ toggleSelectAll });
      return () => h('div', { 'data-testid': `${name}-stub` });
    },
  });
}

const accounts: ChainAddress[] = [{ address: '0x1', chain: 'eth' }];

async function createWrapper(props: { processing?: boolean; disabled?: boolean } = {}): Promise<VueWrapper<InstanceType<typeof HistoryRefreshSelection>>> {
  const wrapper = mount(HistoryRefreshSelection, {
    global: {
      stubs: {
        HistoryRefreshChains: tabStub('HistoryRefreshChains', toggles.chains),
        HistoryRefreshExchanges: tabStub('HistoryRefreshExchanges', toggles.exchanges),
        HistoryRefreshProtocolEvents: tabStub('HistoryRefreshProtocolEvents', toggles.protocols),
        HistoryRefreshStakingEvents: tabStub('HistoryRefreshStakingEvents', toggles.events),
        RuiMenu: RuiMenuStub,
      },
    },
    props: { processing: false, ...props },
  });

  // The tab items only render their content after the first tick, and the template refs the
  // component routes "select all" through are only populated once they have.
  await nextTick();
  return wrapper;
}

describe('historyRefreshSelection', () => {
  let wrapper: VueWrapper<InstanceType<typeof HistoryRefreshSelection>>;

  /** Makes the active tab report a partial selection, which is what enables the refresh button. */
  async function selectAccounts(): Promise<void> {
    const chains = wrapper.findComponent({ name: 'HistoryRefreshChains' });
    chains.vm.$emit('update:modelValue', accounts);
    await nextTick();
  }

  /** Clicks a tab header, the way a user switches tabs. */
  async function openTab(tab: string): Promise<void> {
    const header = wrapper.findAll('button').find(button => button.text() === `history_refresh_selection.tabs.${tab}`);
    assert(header, `no tab header for ${tab}`);
    await header.trigger('click');
    await nextTick();
  }

  beforeEach(async () => {
    vi.clearAllMocks();
    wrapper = await createWrapper();
  });

  afterEach(() => {
    wrapper.unmount();
  });

  it('should keep the refresh button disabled until something is picked', async () => {
    const refresh = wrapper.find('[data-testid=refresh-selection-refresh]');
    expect(refresh.attributes('disabled')).toBeDefined();

    await selectAccounts();

    expect(wrapper.find('[data-testid=refresh-selection-refresh]').attributes('disabled')).toBeUndefined();
  });

  it('should emit the active tab picks and close the menu on refresh', async () => {
    const menu = wrapper.findComponent(RuiMenuStub);
    menu.vm.$emit('update:modelValue', true);
    await nextTick();
    await selectAccounts();

    await wrapper.find('[data-testid=refresh-selection-refresh]').trigger('click');

    expect(wrapper.emitted('refresh')).toEqual([[{ accounts }]]);
    expect(menu.props('modelValue')).toBe(false);
    expect(wrapper.findComponent({ name: 'HistoryRefreshChains' }).props('modelValue')).toEqual([]);
  });

  it('should clear the picks without emitting when cancelled', async () => {
    expect(wrapper.find('[data-testid=refresh-selection-cancel]').exists()).toBe(false);

    await selectAccounts();
    await wrapper.find('[data-testid=refresh-selection-cancel]').trigger('click');

    expect(wrapper.emitted('refresh')).toBeUndefined();
    expect(wrapper.findComponent({ name: 'HistoryRefreshChains' }).props('modelValue')).toEqual([]);
    expect(wrapper.find('[data-testid=refresh-selection-cancel]').exists()).toBe(false);
  });

  it('should route select all to the tab that is showing', async () => {
    await wrapper.find('[data-testid=refresh-selection-select-all] input').trigger('click');

    expect(toggles.chains).toHaveBeenCalledOnce();
    expect(toggles.exchanges).not.toHaveBeenCalled();

    await openTab('exchanges');
    await wrapper.find('[data-testid=refresh-selection-select-all] input').trigger('click');

    expect(toggles.exchanges).toHaveBeenCalledOnce();
    expect(toggles.chains).toHaveBeenCalledOnce();
  });

  it('should forward the search text to the tab components', async () => {
    await wrapper.find('[data-testid=refresh-selection-search] input').setValue('eth');

    expect(wrapper.findComponent({ name: 'HistoryRefreshChains' }).props('search')).toBe('eth');
  });

  it('should forward processing to the tab components and the select all checkbox', async () => {
    wrapper.unmount();
    wrapper = await createWrapper({ processing: true });

    expect(wrapper.findComponent({ name: 'HistoryRefreshChains' }).props('processing')).toBe(true);
    expect(wrapper.find('[data-testid=refresh-selection-select-all] input').attributes('disabled')).toBeDefined();
  });

  it('should disable the activator when disabled', async () => {
    wrapper.unmount();
    wrapper = await createWrapper({ disabled: true });

    expect(wrapper.find('button').attributes('disabled')).toBeDefined();
  });
});
