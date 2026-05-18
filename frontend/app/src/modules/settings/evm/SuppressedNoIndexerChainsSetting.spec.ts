import type { EvmChainInfo } from '@/modules/core/api/types/chains';
import { Blockchain } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SuppressedNoIndexerChainsSetting from '@/modules/settings/evm/SuppressedNoIndexerChainsSetting.vue';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const { computed } = await import('vue');
  const chains: EvmChainInfo[] = [
    {
      evmChainName: 'optimism',
      id: Blockchain.OPTIMISM,
      type: 'evm',
      image: '',
      name: 'Optimism',
      nativeToken: 'ETH',
    },
    {
      evmChainName: 'binance_sc',
      id: 'binance_sc',
      type: 'evm',
      image: '',
      name: 'BNB Smart Chain',
      nativeToken: 'BNB',
    },
  ];
  return {
    useSupportedChains: vi.fn().mockReturnValue({
      txEvmChains: computed(() => chains),
      getChainName: (chain: string): string => chains.find(c => c.id === chain)?.name ?? chain,
    }),
  };
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
      update: vi.fn(),
      updateFrontendSetting: vi.fn().mockResolvedValue({ success: true }),
    }),
  };
});

describe('suppressedNoIndexerChainsSetting', () => {
  let wrapper: VueWrapper<InstanceType<typeof SuppressedNoIndexerChainsSetting>>;

  function createWrapper(): VueWrapper<InstanceType<typeof SuppressedNoIndexerChainsSetting>> {
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(SuppressedNoIndexerChainsSetting, {
      global: { plugins: [pinia] },
      provide: libraryDefaults,
    });
  }

  beforeEach(async (): Promise<void> => {
    wrapper = createWrapper();
    await flushPromises();
  });

  it('should render the suppressed chains setting with no chips by default', () => {
    expect(wrapper.find('[data-cy=suppressed-no-indexer-chains-setting]').exists()).toBe(true);
    expect(wrapper.find('[data-cy=suppressed-no-indexer-chains]').exists()).toBe(true);
    expect(wrapper.findAll('.rui-chip')).toHaveLength(0);
  });

  it('should reflect the suppressed chain in the autocomplete value', async () => {
    const store = useFrontendSettingsStore();
    store.update({ suppressNoIndexerChains: ['binance_sc'] });
    await nextTick();
    await flushPromises();

    expect(wrapper.text()).toContain('BNB Smart Chain');
  });
});
