import type { EvmChainInfo } from '@/modules/core/api/types/chains';
import type PrioritizedList from '@/modules/shell/components/PrioritizedList.vue';
import { Blockchain } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import IndexerOrderSetting from '@/modules/settings/evm/IndexerOrderSetting.vue';
import { EvmIndexer } from '@/modules/settings/types/evm-indexer';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

const chains: EvmChainInfo[] = [
  {
    evmChainName: 'optimism',
    id: Blockchain.OPTIMISM,
    image: '',
    name: 'Optimism',
    nativeToken: 'ETH',
    type: 'evm',
  },
  {
    evmChainName: 'gnosis',
    id: 'gnosis',
    image: '',
    name: 'Gnosis',
    nativeToken: 'XDAI',
    type: 'evm',
  },
];

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const { computed } = await import('vue');
  const mod = await vi.importActual<typeof import('@/modules/core/common/use-supported-chains')>(
    '@/modules/core/common/use-supported-chains',
  );
  return {
    ...mod,
    useSupportedChains: vi.fn().mockReturnValue({
      getChain: (evmChainName: string): string => evmChainName,
      getChainName: (chain: string): string => (chain === 'gnosis' ? 'Gnosis' : 'Optimism'),
      getEvmChainName: (chain: string): string | undefined => chain,
      matchChain: (): undefined => undefined,
      txEvmChains: computed(() => chains),
      useChainImageUrl: () => computed(() => ''),
    }),
  };
});

const push = vi.fn();

vi.mock('vue-router', async () => {
  const mod = await vi.importActual<typeof import('vue-router')>('vue-router');
  return { ...mod, useRouter: vi.fn(() => ({ push })) };
});

vi.mock('@/modules/settings/use-settings-operations', async () => {
  const mod = await vi.importActual<typeof import('@/modules/settings/use-settings-operations')>(
    '@/modules/settings/use-settings-operations',
  );
  return {
    ...mod,
    useSettingsOperations: vi.fn().mockReturnValue({
      applyFrontendSettingLocal: vi.fn(),
      enableModule: vi.fn(),
      setKrakenAccountType: vi.fn(),
      update: vi.fn().mockResolvedValue({ success: true }),
      updateFrontendSetting: vi.fn().mockResolvedValue({ success: true }),
    }),
  };
});

describe('indexerOrderSetting', () => {
  let wrapper: VueWrapper<InstanceType<typeof IndexerOrderSetting>>;

  function createWrapper(): VueWrapper<InstanceType<typeof IndexerOrderSetting>> {
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(IndexerOrderSetting, {
      global: { plugins: [pinia] },
      provide: libraryDefaults,
    });
  }

  async function mountWith(
    defaultEvmIndexerOrder: EvmIndexer[],
    evmIndexersOrder: Record<string, EvmIndexer[]> = {},
  ): Promise<void> {
    wrapper = createWrapper();
    updateGeneralSettings({ defaultEvmIndexerOrder, evmIndexersOrder });
    await nextTick();
    await flushPromises();
  }

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    // The menu teleports to the body; without unmounting, the next test's document query would
    // read this test's leftover menu instead of its own.
    wrapper?.unmount();
    document.body.innerHTML = '';
  });

  it('should render only the default tab when no chain has an override', async () => {
    await mountWith([EvmIndexer.ETHERSCAN, EvmIndexer.BLOCKSCOUT]);

    expect(wrapper.find('[data-testid=indexer-order-setting]').exists()).toBe(true);
    expect(wrapper.findAll('[data-testid=indexer-tab]')).toHaveLength(1);
    expect(wrapper.find('[data-testid=default-indexer-order]').exists()).toBe(true);
  });

  it('should add a tab for each chain that has an override', async () => {
    await mountWith([EvmIndexer.ETHERSCAN], { gnosis: [EvmIndexer.ETHERSCAN] });

    const tabs = wrapper.findAll('[data-testid=indexer-tab]');
    expect(tabs).toHaveLength(2);
    expect(tabs[1].attributes('data-key')).toBe('gnosis');
  });

  /** The menu content is teleported out of the wrapper, so it has to be read off the document. */
  async function openChainMenu(): Promise<HTMLElement[]> {
    await wrapper.find('[data-testid=add-chain-button]').trigger('click');
    await flushPromises();
    return Array.from(document.querySelectorAll<HTMLElement>('[data-testid=chain-menu-item]'));
  }

  it('should offer only the chains without an override in the add menu', async () => {
    await mountWith([EvmIndexer.ETHERSCAN], { gnosis: [EvmIndexer.ETHERSCAN] });

    const options = await openChainMenu();

    expect(options).toHaveLength(1);
    expect(options[0].dataset.key).toBe(Blockchain.OPTIMISM);
  });

  it('should disable the add button once every chain has an override', async () => {
    await mountWith([EvmIndexer.ETHERSCAN], {
      gnosis: [EvmIndexer.ETHERSCAN],
      optimism: [EvmIndexer.ETHERSCAN],
    });

    expect(wrapper.find('[data-testid=add-chain-button]').attributes('disabled')).toBeDefined();
  });

  it('should persist the new chain order keyed by evm chain name', async () => {
    await mountWith([EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN]);

    const [option] = await openChainMenu();
    option.click();
    await flushPromises();

    const { update } = useSettingsOperations();
    expect(update).toHaveBeenCalledWith({
      evmIndexersOrder: { optimism: [EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN] },
    });
  });

  it('should prompt for an api key when the leading indexer needs one', async () => {
    await mountWith([EvmIndexer.ETHERSCAN, EvmIndexer.ROUTESCAN]);

    expect(wrapper.find('[data-testid=missing-api-key-alert]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=missing-api-key-alert]').text()).toContain('Etherscan');
  });

  it('should not prompt for an api key when the leading indexer needs none', async () => {
    await mountWith([EvmIndexer.ROUTESCAN, EvmIndexer.ETHERSCAN]);

    expect(wrapper.find('[data-testid=missing-api-key-alert]').exists()).toBe(false);
  });

  it('should warn about the chains with indexer caveats', async () => {
    await mountWith([EvmIndexer.ETHERSCAN], { gnosis: [EvmIndexer.ETHERSCAN] });
    await selectTab('gnosis');

    const warnings = wrapper.findAll('[data-testid=chain-warning-alert]');
    expect(warnings).toHaveLength(1);
    expect(warnings[0].text()).toBe('evm_settings.indexer.chain_warnings.gnosis_key_required');
  });

  it('should not warn on the default tab', async () => {
    await mountWith([EvmIndexer.ETHERSCAN], { gnosis: [EvmIndexer.ETHERSCAN] });

    expect(wrapper.findAll('[data-testid=chain-warning-alert]')).toHaveLength(0);
  });

  async function selectTab(tab: string): Promise<void> {
    await wrapper.find(`[data-testid=indexer-tab][data-key="${tab}"]`).trigger('click');
    await nextTick();
  }

  function defaultList(): VueWrapper<InstanceType<typeof PrioritizedList>> {
    return wrapper.findComponent<typeof PrioritizedList>('[data-testid=default-indexer-order]');
  }

  function chainList(): VueWrapper<InstanceType<typeof PrioritizedList>> {
    return wrapper.findComponent<typeof PrioritizedList>('[data-testid=chain-indexer-order]');
  }

  it('should apply a reordered default order', async () => {
    await mountWith([EvmIndexer.ETHERSCAN, EvmIndexer.BLOCKSCOUT]);
    expect(defaultList().props('modelValue')).toEqual([EvmIndexer.ETHERSCAN, EvmIndexer.BLOCKSCOUT]);

    defaultList().vm.$emit('update:model-value', [EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN]);
    await nextTick();

    expect(defaultList().props('modelValue')).toEqual([EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN]);
  });

  it('should re-evaluate the api key prompt after a reorder', async () => {
    await mountWith([EvmIndexer.ROUTESCAN, EvmIndexer.ETHERSCAN]);
    expect(wrapper.find('[data-testid=missing-api-key-alert]').exists()).toBe(false);

    defaultList().vm.$emit('update:model-value', [EvmIndexer.ETHERSCAN, EvmIndexer.ROUTESCAN]);
    await nextTick();

    expect(wrapper.find('[data-testid=missing-api-key-alert]').exists()).toBe(true);
  });

  it('should apply a reordered chain order', async () => {
    await mountWith([EvmIndexer.ETHERSCAN], { gnosis: [EvmIndexer.ETHERSCAN, EvmIndexer.BLOCKSCOUT] });
    await selectTab('gnosis');

    chainList().vm.$emit('update:model-value', [EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN]);
    await nextTick();

    expect(chainList().props('modelValue')).toEqual([EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN]);
  });

  it('should persist the remaining overrides when a chain is removed', async () => {
    await mountWith([EvmIndexer.ETHERSCAN], {
      gnosis: [EvmIndexer.ETHERSCAN],
      optimism: [EvmIndexer.ETHERSCAN],
    });

    wrapper.findAllComponents({ name: 'IndexerTabLabel' })[0].vm.$emit('remove', 'gnosis');
    await flushPromises();

    const { update } = useSettingsOperations();
    expect(update).toHaveBeenCalledWith({ evmIndexersOrder: { optimism: [EvmIndexer.ETHERSCAN] } });
    expect(wrapper.findAll('[data-testid=indexer-tab]')).toHaveLength(2);
  });

  it('should return to the default tab when the open chain is removed', async () => {
    await mountWith([EvmIndexer.ETHERSCAN], { gnosis: [EvmIndexer.ETHERSCAN] });
    await selectTab('gnosis');
    expect(chainList().exists()).toBe(true);

    wrapper.findAllComponents({ name: 'IndexerTabLabel' })[0].vm.$emit('remove', 'gnosis');
    await flushPromises();

    expect(wrapper.find('[data-testid=default-indexer-order]').exists()).toBe(true);
  });

  it('should route to the api key page for the indexer it asks about', async () => {
    await mountWith([EvmIndexer.ETHERSCAN, EvmIndexer.ROUTESCAN]);

    await wrapper.find('[data-testid=missing-api-key-alert] button').trigger('click');
    await flushPromises();

    expect(push).toHaveBeenCalledWith({
      name: '/api-keys/external/',
      query: { service: EvmIndexer.ETHERSCAN },
    });
  });
});
