import { Blockchain } from '@rotki/common';
import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { defineComponent, h, type Ref } from 'vue';
import { RpcSettingKey, tabKey, useRpcSettingsTabs, type UseRpcSettingsTabsReturn } from '@/modules/settings/general/rpc/use-rpc-settings-tabs';

interface MockChain {
  id: string;
  type: 'evm';
  name: string;
}

const { txEvmChainsRef, useRouteMock, useRouterMock } = await vi.hoisted(async () => {
  const vue = await import('vue');
  return {
    txEvmChainsRef: vue.ref<MockChain[]>([]),
    useRouteMock: vi.fn(),
    useRouterMock: vi.fn(),
  };
});

vi.mock('vue-router', () => ({
  useRoute: useRouteMock,
  useRouter: useRouterMock,
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn().mockReturnValue({
    txEvmChains: txEvmChainsRef,
    getChainName: (id: string): string => txEvmChainsRef.value.find(c => c.id === id)?.name ?? id,
  }),
}));

function mountWithComposable(): { wrapper: ReturnType<typeof mount>; result: UseRpcSettingsTabsReturn } {
  let captured: UseRpcSettingsTabsReturn | undefined;
  const Host = defineComponent({
    setup(): () => ReturnType<typeof h> {
      captured = useRpcSettingsTabs();
      return (): ReturnType<typeof h> => h('div');
    },
  });
  const wrapper = mount(Host);
  return { result: captured!, wrapper };
}

describe('useRpcSettingsTabs', () => {
  let mockRoute: Ref<{ query: Record<string, unknown> }>;
  let mockRouter: { replace: Mock };

  beforeEach(() => {
    const emptyQuery: Record<string, unknown> = {};
    mockRoute = ref({ query: emptyQuery });
    mockRouter = {
      replace: vi.fn(async ({ query }: { query: Record<string, unknown> }) => {
        set(mockRoute, { query });
      }),
    };
    useRouteMock.mockReturnValue(mockRoute);
    useRouterMock.mockReturnValue(mockRouter);
    set(txEvmChainsRef, [
      { id: 'eth', name: 'Ethereum', type: 'evm' },
      { id: 'optimism', name: 'Optimism', type: 'evm' },
      { id: 'base', name: 'Base', type: 'evm' },
    ]);
  });

  describe('selection', () => {
    it('should default selection to Ethereum', () => {
      const { result } = mountWithComposable();
      expect(result.selectedKey.value).toBe(Blockchain.ETH);
    });

    it('should read the initial selection from the route query on mount', async () => {
      set(mockRoute, { query: { tab: 'eth_consensus_layer' } });
      const { result } = mountWithComposable();
      await flushPromises();
      expect(result.selectedKey.value).toBe('eth_consensus_layer');
    });

    it('should react to ?tab= changes while mounted', async () => {
      const { result } = mountWithComposable();
      await flushPromises();
      expect(result.selectedKey.value).toBe(Blockchain.ETH);

      set(mockRoute, { query: { tab: 'eth_consensus_layer' } });
      await flushPromises();
      expect(result.selectedKey.value).toBe('eth_consensus_layer');
    });

    it('should update the URL when selectTab is called', async () => {
      const { result } = mountWithComposable();
      result.selectTab('ksm');
      await flushPromises();
      expect(mockRouter.replace).toHaveBeenCalledWith({ query: { tab: 'ksm' } });
    });

    it('should not push a URL update when tab already matches', async () => {
      set(mockRoute, { query: { tab: 'ksm' } });
      const { result } = mountWithComposable();
      await flushPromises();
      mockRouter.replace.mockClear();
      result.selectTab('ksm');
      await flushPromises();
      expect(mockRouter.replace).not.toHaveBeenCalled();
    });

    it('should ignore empty selectTab values', async () => {
      const { result } = mountWithComposable();
      result.selectTab(null);
      result.selectTab(undefined);
      result.selectTab('');
      expect(result.selectedKey.value).toBe(Blockchain.ETH);
    });

    it('should preserve selection when txEvmChains populates after mount', async () => {
      // Regression: the previous index-based selection lost the user's tab
      // when the chain list arrived asynchronously.
      set(txEvmChainsRef, []);
      set(mockRoute, { query: { tab: 'eth_consensus_layer' } });
      const { result } = mountWithComposable();
      await flushPromises();
      expect(result.selectedKey.value).toBe('eth_consensus_layer');

      set(txEvmChainsRef, [
        { id: 'eth', name: 'Ethereum', type: 'evm' },
        { id: 'optimism', name: 'Optimism', type: 'evm' },
      ]);
      await flushPromises();
      expect(result.selectedKey.value).toBe('eth_consensus_layer');
      expect(result.activeTab.value).toBeDefined();
      expect(result.activeTab.value && 'id' in result.activeTab.value
        ? result.activeTab.value.id
        : undefined).toBe('eth_consensus_layer');
    });
  });

  describe('groups', () => {
    it('should split EVM chains and other endpoints into separate groups', () => {
      const { result } = mountWithComposable();
      const evmKeys = result.evmRailOptions.value.map(o => o.key);
      const otherKeys = result.otherRailOptions.value.map(o => o.key);
      expect(evmKeys).toEqual(['eth', 'optimism', 'base']);
      expect(otherKeys).toEqual([Blockchain.SOLANA, 'btc_mempool_space', Blockchain.KSM, Blockchain.DOT, 'eth_consensus_layer']);
    });

    it('should expose Solana as the first other-group entry', () => {
      const { result } = mountWithComposable();
      expect(result.firstOtherKey.value).toBe(Blockchain.SOLANA);
    });

    it('should put Solana in the other group, not EVM', () => {
      const { result } = mountWithComposable();
      expect(result.evmRailOptions.value.find(o => o.key === Blockchain.SOLANA)).toBeUndefined();
      expect(result.otherRailOptions.value.find(o => o.key === Blockchain.SOLANA)).toBeDefined();
    });

    it('should concatenate EVM and other into allRailOptions in order', () => {
      const { result } = mountWithComposable();
      const all = result.allRailOptions.value.map(o => o.key);
      expect(all).toEqual([
        'eth',
        'optimism',
        'base',
        Blockchain.SOLANA,
        'btc_mempool_space',
        Blockchain.KSM,
        Blockchain.DOT,
        'eth_consensus_layer',
      ]);
    });

    it('should label rail options with chain names', () => {
      const { result } = mountWithComposable();
      const ethOption = result.evmRailOptions.value.find(o => o.key === 'eth');
      expect(ethOption?.label).toBe('Ethereum');
    });
  });

  describe('canAddNode', () => {
    it('should be true on EVM chains', () => {
      const { result } = mountWithComposable();
      result.selectTab('eth');
      expect(result.canAddNode.value).toBe(true);
    });

    it('should be true on Solana', () => {
      const { result } = mountWithComposable();
      result.selectTab(Blockchain.SOLANA);
      expect(result.canAddNode.value).toBe(true);
    });

    it.each([
      ['btc_mempool_space'],
      [Blockchain.KSM],
      [Blockchain.DOT],
      ['eth_consensus_layer'],
    ])('should be false on single-value endpoint %s', (key) => {
      const { result } = mountWithComposable();
      result.selectTab(key);
      expect(result.canAddNode.value).toBe(false);
    });
  });

  describe('tabKey helper', () => {
    it('should return chain id for chain tabs', () => {
      expect(tabKey({ chain: Blockchain.ETH })).toBe(Blockchain.ETH);
    });

    it('should return custom id for custom tabs', () => {
      expect(tabKey({
        id: 'eth_consensus_layer',
        image: '',
        name: 'ETH Beacon Node',
        setting: RpcSettingKey.BEACON,
      })).toBe('eth_consensus_layer');
    });
  });
});
