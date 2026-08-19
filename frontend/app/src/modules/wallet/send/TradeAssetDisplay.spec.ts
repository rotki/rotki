import type { ComputedRef } from 'vue';
import type { TradableAsset } from '@/modules/wallet/types';
import { bigNumberify } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TradeAssetDisplay from '@/modules/wallet/send/TradeAssetDisplay.vue';

const useAssetField = vi.fn<(identifier: unknown, field: string) => ComputedRef<string>>();

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: vi.fn(() => ({ useAssetField })),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({ getEvmChainName: (chain: string): string => chain })),
}));

const ASSET: TradableAsset = {
  amount: bigNumberify(1),
  asset: 'eip155:1/erc20:0xaaa',
  chain: 'eth',
};

describe('tradeAssetDisplay', () => {
  function createWrapper(props: Record<string, unknown> = {}): VueWrapper {
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(TradeAssetDisplay, {
      global: {
        plugins: [pinia],
        provide: libraryDefaults,
        stubs: { AssetDetails: true },
      },
      props: { data: ASSET, list: true, ...props },
    });
  }

  beforeEach(() => {
    vi.clearAllMocks();
    useAssetField.mockImplementation((_identifier: unknown, field: string) =>
      computed(() => (field === 'symbol' ? 'RESOLVED_SYM' : 'RESOLVED_NAME')));
  });

  it('should resolve the symbol and name itself when none are provided', () => {
    const wrapper = createWrapper();

    expect(wrapper.text()).toContain('RESOLVED_SYM');
    expect(wrapper.text()).toContain('RESOLVED_NAME');
  });

  it('should prefer a provided symbol and name over resolving', () => {
    const wrapper = createWrapper({ name: 'Zeus Finance', symbol: 'ZEU' });

    expect(wrapper.text()).toContain('ZEU');
    expect(wrapper.text()).toContain('Zeus Finance');
    expect(wrapper.text()).not.toContain('RESOLVED_SYM');
    expect(wrapper.text()).not.toContain('RESOLVED_NAME');
  });

  it('should not evaluate the resolution when both are provided', () => {
    const resolver = vi.fn(() => 'RESOLVED');
    useAssetField.mockImplementation(() => computed(resolver));

    createWrapper({ name: 'Zeus Finance', symbol: 'ZEU' });

    // The computeds are created but never read, so the lazy body must not run: this is what makes
    // the pre-resolved props an actual saving rather than a cosmetic one.
    expect(resolver).not.toHaveBeenCalled();
  });

  it('should still resolve the half that was not provided', () => {
    const wrapper = createWrapper({ symbol: 'ZEU' });

    expect(wrapper.text()).toContain('ZEU');
    expect(wrapper.text()).toContain('RESOLVED_NAME');
  });

  it('should treat an empty provided symbol as a value rather than falling back', () => {
    const wrapper = createWrapper({ symbol: '' });

    expect(wrapper.text()).not.toContain('RESOLVED_SYM');
  });
});
