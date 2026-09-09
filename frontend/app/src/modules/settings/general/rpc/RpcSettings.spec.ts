import { Blockchain } from '@rotki/common';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, type VNode } from 'vue';
import RpcSettings from '@/modules/settings/general/rpc/RpcSettings.vue';
import {
  RpcSettingKey,
  type RpcSettingTab,
  type UseRpcSettingsTabsReturn,
} from '@/modules/settings/general/rpc/use-rpc-settings-tabs';

const {
  addNewRpcNode,
  canAddNode,
  isMdAndUp,
  loadNodes,
  reload,
  rpcSettingTabs,
  selectedKey,
  selectTab,
} = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  const { Blockchain: Chain } = await import('@rotki/common');
  return {
    addNewRpcNode: vi.fn(),
    canAddNode: ref<boolean>(true),
    isMdAndUp: ref<boolean>(true),
    loadNodes: vi.fn(async () => {}),
    reload: vi.fn(async () => {}),
    rpcSettingTabs: ref<RpcSettingTab[]>([]),
    selectedKey: ref<string>(Chain.ETH),
    selectTab: vi.fn(),
  };
});

vi.mock('@/modules/settings/general/rpc/use-rpc-settings-tabs', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/settings/general/rpc/use-rpc-settings-tabs')>(),
  useRpcSettingsTabs: (): UseRpcSettingsTabsReturn => ({
    activeTab: computed(() => get(rpcSettingTabs)[0]),
    allRailOptions: computed(() => []),
    canAddNode: computed<boolean>(() => get(canAddNode)),
    evmRailOptions: computed(() => []),
    firstOtherKey: computed(() => undefined),
    nodeChains: computed(() => [Blockchain.ETH]),
    otherRailOptions: computed(() => []),
    rpcSettingTabs: computed(() => get(rpcSettingTabs)),
    selectedKey,
    selectTab,
  }),
}));

vi.mock('@rotki/ui-library', async importOriginal => ({
  ...await importOriginal<typeof import('@rotki/ui-library')>(),
  useBreakpoint: (): Record<string, unknown> => ({ isMdAndUp }),
}));

/**
 * Stands in for the chain manager, which exposes both the add and the reload entry points.
 *
 * @remarks
 * The managers are loaded through `defineAsyncComponent`, which only unwraps the `default` export
 * of a module that says it is one. Without `__esModule` the mock namespace is taken for the
 * component itself, and every property Vue reads off it fails as a missing export.
 */
vi.mock('@/modules/settings/general/rpc/BlockchainRpcNodeManager.vue', async () => {
  const { defineComponent, h } = await import('vue');
  return {
    __esModule: true,
    default: defineComponent({
      name: 'BlockchainRpcNodeManager',
      setup(_props, { expose }): () => VNode {
        expose({ addNewRpcNode, loadNodes });
        return () => h('div', { 'data-testid': 'chain-manager' });
      },
    }),
  };
});

/** The simple manager has no node list to re-read, so it exposes only the add entry point. */
vi.mock('@/modules/settings/general/rpc/simple/SimpleRpcNodeManager.vue', async () => {
  const { defineComponent, h } = await import('vue');
  return {
    __esModule: true,
    default: defineComponent({
      name: 'SimpleRpcNodeManager',
      setup(_props, { expose }): () => VNode {
        expose({ addNewRpcNode });
        return () => h('div', { 'data-testid': 'simple-manager' });
      },
    }),
  };
});

vi.mock('@/modules/settings/general/rpc/providers/RpcProviderKeys.vue', async () => {
  const { defineComponent, h } = await import('vue');
  return {
    default: defineComponent({
      emits: ['removed'],
      name: 'RpcProviderKeys',
      setup(_props, { emit, expose }): () => VNode {
        expose({ reload });
        return () => h('button', { 'data-testid': 'provider-keys', 'onClick': () => emit('removed') });
      },
    }),
  };
});

const RuiTabStub = defineComponent({
  emits: ['click'],
  props: ['active'],
  template: '<button role="tab" :aria-selected="active" @click="$emit(\'click\')"><slot /></button>',
});

const CHAIN_TAB: RpcSettingTab = { chain: Blockchain.ETH };
const SETTING_TAB: RpcSettingTab = { chain: Blockchain.KSM, setting: RpcSettingKey.KSM };

async function createWrapper(): Promise<VueWrapper<any>> {
  const wrapper = mount(RpcSettings, {
    global: {
      stubs: {
        RpcSettingOption: true,
        RuiMenuSelect: true,
        RuiTab: RuiTabStub,
        RuiTabs: { template: '<div><slot /></div>' },
        SettingCategoryHeader: true,
      },
    },
  });
  await flushPromises();
  return wrapper;
}

describe('rpcSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(canAddNode, true);
    set(isMdAndUp, true);
    set(rpcSettingTabs, [CHAIN_TAB]);
    set(selectedKey, Blockchain.ETH);
  });

  describe('the manager on screen', () => {
    it('should show the chain manager for a chain tab', async () => {
      const wrapper = await createWrapper();

      expect(wrapper.find('[data-testid=chain-manager]').exists()).toBe(true);
    });

    it('should show the simple manager for a tab backed by a single setting', async () => {
      set(rpcSettingTabs, [SETTING_TAB]);
      set(selectedKey, Blockchain.KSM);

      const wrapper = await createWrapper();

      expect(wrapper.find('[data-testid=simple-manager]').exists()).toBe(true);
    });

    it('should show only the selected tab', async () => {
      set(rpcSettingTabs, [CHAIN_TAB, SETTING_TAB]);

      const wrapper = await createWrapper();

      expect(wrapper.find('[data-testid=chain-manager]').exists()).toBe(true);
      expect(wrapper.find('[data-testid=simple-manager]').exists()).toBe(false);
    });
  });

  /** The button belongs to the header, so it reaches the manager on screen through its ref. */
  describe('adding a node', () => {
    it('should ask the manager on screen to add one', async () => {
      const wrapper = await createWrapper();

      await wrapper.find('[data-testid=add-node]').trigger('click');

      expect(addNewRpcNode).toHaveBeenCalledTimes(1);
    });

    it('should hide the button when the tab takes no new nodes', async () => {
      set(canAddNode, false);

      const wrapper = await createWrapper();

      expect(wrapper.find('[data-testid=add-node]').exists()).toBe(false);
    });
  });

  /**
   * Removing a provider's keys deletes nodes, which may have emptied the chain on screen, so its
   * list is re-read. Only the chain manager holds one.
   */
  describe('after a provider key is removed', () => {
    it('should re-read the chain manager list', async () => {
      const wrapper = await createWrapper();

      await wrapper.find('[data-testid=provider-keys]').trigger('click');

      expect(loadNodes).toHaveBeenCalledTimes(1);
    });

    it('should leave the simple manager alone, which has no list to re-read', async () => {
      set(rpcSettingTabs, [SETTING_TAB]);
      set(selectedKey, Blockchain.KSM);
      const wrapper = await createWrapper();

      await wrapper.find('[data-testid=provider-keys]').trigger('click');

      expect(loadNodes).not.toHaveBeenCalled();
    });
  });

  /** A fan-out adds nodes to chains the provider chips count, so the chips are re-read. */
  it('should re-read the provider keys once the manager is done', async () => {
    const wrapper = await createWrapper();

    wrapper.findComponent({ name: 'BlockchainRpcNodeManager' }).vm.$emit('complete');
    await nextTick();

    expect(reload).toHaveBeenCalledTimes(1);
  });

  describe('picking a tab', () => {
    it('should show the rail on a wide screen', async () => {
      const wrapper = await createWrapper();

      expect(wrapper.find('[data-testid=rpc-settings-rail]').exists()).toBe(true);
      expect(wrapper.find('[data-testid=rpc-settings-dropdowns]').exists()).toBe(false);
    });

    it('should fall back to a dropdown on a narrow one', async () => {
      set(isMdAndUp, false);

      const wrapper = await createWrapper();

      expect(wrapper.find('[data-testid=rpc-settings-dropdowns]').exists()).toBe(true);
      expect(wrapper.find('[data-testid=rpc-settings-rail]').exists()).toBe(false);
    });
  });
});
