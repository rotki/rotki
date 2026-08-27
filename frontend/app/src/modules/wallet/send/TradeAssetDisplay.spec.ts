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

    expect(resolver).not.toHaveBeenCalled();
  });

  it('should still resolve the half that was not provided', () => {
    const wrapper = createWrapper({ symbol: 'ZEU' });

    expect(wrapper.text()).toContain('ZEU');
    expect(wrapper.text()).toContain('RESOLVED_NAME');
  });

  it('should show the balance on a list row when there is an amount', () => {
    const wrapper = createWrapper({
      data: { ...ASSET, amount: bigNumberify(42), fiatValue: bigNumberify(100) },
    });

    expect(wrapper.find('[data-testid="trade-asset-balance"]').exists()).toBe(true);
  });

  it('should hide the balance when the amount is zero, as every row is until a wallet connects', () => {
    const wrapper = createWrapper({ data: { ...ASSET, amount: bigNumberify(0) } });

    expect(wrapper.find('[data-testid="trade-asset-balance"]').exists()).toBe(false);
  });

  it('should not show a balance outside a list row', () => {
    const wrapper = createWrapper({
      data: { ...ASSET, amount: bigNumberify(42) },
      list: false,
    });

    expect(wrapper.find('[data-testid="trade-asset-balance"]').exists()).toBe(false);
  });

  it('should show the address only when one is provided', () => {
    expect(createWrapper().find('[data-testid="trade-asset-address"]').exists()).toBe(false);

    const wrapper = createWrapper({ address: '0x1f98…F984' });
    expect(wrapper.find('[data-testid="trade-asset-address"]').text()).toBe('0x1f98…F984');
  });

  it('should mark the selected row', () => {
    expect(createWrapper().find('[data-testid="trade-asset-selected"]').exists()).toBe(false);
    expect(createWrapper({ selected: true }).find('[data-testid="trade-asset-selected"]').exists()).toBe(true);
  });

  it('should treat an empty provided symbol as a value rather than falling back', () => {
    const wrapper = createWrapper({ symbol: '' });

    expect(wrapper.text()).not.toContain('RESOLVED_SYM');
  });
});
