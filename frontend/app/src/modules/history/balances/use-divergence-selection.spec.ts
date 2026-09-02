import { mount, type VueWrapper } from '@vue/test-utils';
import { get, set } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, nextTick } from 'vue';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useDivergenceSelection } from '@/modules/history/balances/use-divergence-selection';
import { useHistoryStore } from '@/modules/history/use-history-store';

const mockFetchLocationLabels = vi.fn();

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({
    getEvmChainName: (chain: string): string | undefined => chain === 'eth' ? 'ethereum' : undefined,
    isEvm: (chain: string): boolean => chain === 'eth',
    matchChain: (location: string): string | undefined => {
      if (['eth', 'ethereum'].includes(location))
        return 'eth';
      return ['btc', 'bitcoin'].includes(location) ? 'btc' : undefined;
    },
  }),
}));

vi.mock('@/modules/history/use-history-data-fetching', () => ({
  useHistoryDataFetching: (): object => ({
    fetchLocationLabels: mockFetchLocationLabels,
  }),
}));

function mountSelection(): { wrapper: VueWrapper; result: ReturnType<typeof useDivergenceSelection> } {
  let result!: ReturnType<typeof useDivergenceSelection>;
  const wrapper = mount(defineComponent({
    render: () => null,
    setup() {
      result = useDivergenceSelection();
      return {};
    },
  }));
  return { result, wrapper };
}

describe('useDivergenceSelection', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mockFetchLocationLabels.mockReset();
    mockFetchLocationLabels.mockResolvedValue(undefined);
    useHistoryStore().setLocationLabels([]);
    useBlockchainAccountsStore().updateAccounts('eth', [{
      chain: 'eth',
      data: {
        address: '0xA',
        type: 'address',
      },
      nativeAsset: 'ETH',
    }]);
  });

  it('should build chain and location-label options from tracked evm accounts', async () => {
    const { result } = mountSelection();
    await nextTick();

    expect(get(result.chainOptions)).toStrictEqual(['eth']);
    expect(get(result.locationLabelOptions)).toStrictEqual([{ location: 'eth', locationLabel: '0xA' }]);
  });

  it('should default the selected chain, label and evm chain to the first valid option', async () => {
    const { result } = mountSelection();
    await nextTick();

    expect(get(result.modelSelectedChain)).toBe('eth');
    expect(get(result.modelSelectedLocationLabel)).toBe('0xA');
    expect(get(result.selectedEvmChain)).toBe('ethereum');
  });

  it('should not offer a location label from a non-evm chain', async () => {
    useHistoryStore().setLocationLabels([
      { location: 'bitcoin', locationLabel: '1Dk75NPu6QXxMxRECfz6VM6oXq3XwprsDF' },
    ]);
    const { result } = mountSelection();
    await nextTick();

    expect(get(result.chainOptions)).toStrictEqual(['eth']);
    expect(get(result.locationLabelOptions)).toStrictEqual([{ location: 'eth', locationLabel: '0xA' }]);
  });

  it('should fetch the location labels on mount', () => {
    mountSelection();

    expect(mockFetchLocationLabels).toHaveBeenCalledOnce();
  });

  it('should clear the selected asset when the chain changes', async () => {
    const { result } = mountSelection();
    await nextTick();

    set(result.modelSelectedAsset, 'eip155:42161/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1');
    set(result.modelSelectedChain, 'arbitrum_one');
    await nextTick();

    expect(get(result.modelSelectedAsset)).toBeUndefined();
  });
});
