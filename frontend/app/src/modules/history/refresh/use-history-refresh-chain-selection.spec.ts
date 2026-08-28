import type { ChainAddress } from '@/modules/history/events/event-payloads';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, nextTick, ref } from 'vue';
import { useHistoryRefreshChainSelection } from './use-history-refresh-chain-selection';

const { addressesByChain, bitcoinChainsData, evmLikeChainsData, solanaChainsData, txEvmChains } = await vi.hoisted(
  async () => {
    const { ref } = await import('vue');
    return {
      addressesByChain: ref<Record<string, string[]>>({}),
      bitcoinChainsData: ref<{ id: string; name: string }[]>([]),
      evmLikeChainsData: ref<{ id: string; name: string }[]>([]),
      solanaChainsData: ref<{ id: string; name: string }[]>([]),
      txEvmChains: ref<{ id: string; name: string }[]>([]),
    };
  },
);

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): Record<string, unknown> => ({
    bitcoinChainsData,
    evmLikeChainsData,
    solanaChainsData,
    txEvmChains,
  }),
}));

vi.mock('@/modules/balances/blockchain/use-account-addresses', () => ({
  useAccountAddresses: (): Record<string, unknown> => ({
    getAddresses: (chain: string): string[] => get(addressesByChain)[chain] ?? [],
  }),
}));

let scope: ReturnType<typeof effectScope>;

interface Harness {
  api: ReturnType<typeof useHistoryRefreshChainSelection>;
  chain: ReturnType<typeof ref<string | undefined>>;
  modelValue: ReturnType<typeof ref<ChainAddress[]>>;
  onAllSelected: ReturnType<typeof vi.fn<(allSelected: boolean) => void>>;
  search: ReturnType<typeof ref<string>>;
}

function harness(selectedChain?: string): Harness {
  const chain = ref<string | undefined>(selectedChain);
  const modelValue = ref<ChainAddress[]>([]);
  const search = ref<string>('');
  const onAllSelected = vi.fn<(allSelected: boolean) => void>();
  scope = effectScope();
  const api = scope.run(() => useHistoryRefreshChainSelection({ chain, modelValue, onAllSelected, search }))!;
  return { api, chain, modelValue, onAllSelected, search };
}

describe('modules/history/refresh/useHistoryRefreshChainSelection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(txEvmChains, [{ id: 'ethereum', name: 'Ethereum' }, { id: 'optimism', name: 'Optimism' }]);
    set(evmLikeChainsData, [{ id: 'zksync_lite', name: 'zkSync Lite' }]);
    set(bitcoinChainsData, [{ id: 'btc', name: 'Bitcoin' }]);
    set(solanaChainsData, [{ id: 'solana', name: 'Solana' }]);
    set(addressesByChain, {
      btc: ['bc1qaaa'],
      ethereum: ['0xaaa', '0xbbb'],
      optimism: [],
      solana: ['sol1'],
      zksync_lite: ['0xccc'],
    });
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('the chains it offers', () => {
    it('should list every kind of chain the app can refresh', () => {
      const { api } = harness();

      expect(get(api.filtered).map(item => item.id)).toEqual(['ethereum', 'zksync_lite', 'btc', 'solana']);
    });

    it('should leave out a chain the user holds no account on', () => {
      const { api } = harness();

      expect(get(api.filtered).map(item => item.id)).not.toContain('optimism');
    });

    it.each([
      ['bitcoin', ['btc']],
      ['sol', ['solana']],
      ['zk', ['zksync_lite']],
    ])('should match %s against both the chain id and its name', (query, expected) => {
      const { api, search } = harness();

      set(search, query);

      expect(get(api.filtered).map(item => item.id)).toEqual(expected);
    });

    it('should carry every address per chain, whether it is selected or not', () => {
      const { api } = harness();

      expect(get(api.chainAddresses)).toEqual({
        btc: ['bc1qaaa'],
        ethereum: ['0xaaa', '0xbbb'],
        optimism: [],
        solana: ['sol1'],
        zksync_lite: ['0xccc'],
      });
    });
  });

  describe('what it starts from', () => {
    it('should select nothing, so a refresh never runs wider than asked', () => {
      const { api, modelValue } = harness();

      expect(get(modelValue)).toEqual([]);
      expect(get(api.modelSelection)).toEqual({
        btc: [],
        ethereum: [],
        optimism: [],
        solana: [],
        zksync_lite: [],
      });
    });

    it('should report that nothing is fully selected', () => {
      const { onAllSelected } = harness();

      expect(onAllSelected).toHaveBeenLastCalledWith(false);
    });
  });

  describe('selecting everything', () => {
    it('should pair each address with its own chain', () => {
      const { api, modelValue } = harness();

      api.toggleSelectAll();

      expect(get(modelValue)).toEqual([
        { address: '0xaaa', chain: 'ethereum' },
        { address: '0xbbb', chain: 'ethereum' },
        { address: '0xccc', chain: 'zksync_lite' },
        { address: 'bc1qaaa', chain: 'btc' },
        { address: 'sol1', chain: 'solana' },
      ]);
    });

    it('should report that everything is now selected', () => {
      const { api, onAllSelected } = harness();

      api.toggleSelectAll();

      expect(onAllSelected).toHaveBeenLastCalledWith(true);
    });

    it('should clear the selection when it is toggled again', () => {
      const { api, modelValue } = harness();

      api.toggleSelectAll();
      api.toggleSelectAll();

      expect(get(modelValue)).toEqual([]);
    });

    it('should not hand out the chain address arrays themselves', () => {
      const { api } = harness();

      api.toggleSelectAll();
      get(api.modelSelection).ethereum.push('0xddd');

      expect(get(api.chainAddresses).ethereum).toEqual(['0xaaa', '0xbbb']);
    });
  });

  describe('selecting within one chain', () => {
    it('should select only that chain, leaving the others alone', () => {
      const { api, modelValue } = harness('ethereum');

      api.toggleSelectAll();

      expect(get(modelValue)).toEqual([
        { address: '0xaaa', chain: 'ethereum' },
        { address: '0xbbb', chain: 'ethereum' },
      ]);
    });

    it('should report that chain as fully selected', () => {
      const { api, onAllSelected } = harness('ethereum');

      api.toggleSelectAll();

      expect(onAllSelected).toHaveBeenLastCalledWith(true);
    });

    it('should clear only that chain when toggled again', () => {
      const { api, modelValue } = harness('ethereum');

      api.toggleSelectAll();
      api.toggleSelectAll();

      expect(get(modelValue)).toEqual([]);
    });

    it('should not report a partly selected chain as fully selected', async () => {
      const { api, onAllSelected } = harness('ethereum');

      get(api.modelSelection).ethereum = ['0xaaa'];
      await nextTick();

      expect(onAllSelected).toHaveBeenLastCalledWith(false);
    });
  });

  describe('when the picked chain changes', () => {
    it('should clear the search, which was scoped to the previous view', async () => {
      const { chain, search } = harness();
      set(search, 'ethereum');

      set(chain, 'btc');
      await nextTick();

      expect(get(search)).toBe('');
    });

    it('should re-report against the newly picked chain', async () => {
      const { api, chain, onAllSelected } = harness();
      api.toggleSelectAll();

      set(chain, 'btc');
      await nextTick();

      expect(onAllSelected).toHaveBeenLastCalledWith(true);
    });
  });

  describe('when a row changes the selection directly', () => {
    it('should keep the accounts to refresh in step', async () => {
      const { api, modelValue } = harness();

      set(api.modelSelection, { ...get(api.modelSelection), btc: ['bc1qaaa'] });
      await nextTick();

      expect(get(modelValue)).toEqual([{ address: 'bc1qaaa', chain: 'btc' }]);
    });

    it('should report everything selected once every address is picked', async () => {
      const { api, onAllSelected } = harness();

      const selection = get(api.modelSelection);
      selection.ethereum = ['0xaaa', '0xbbb'];
      selection.zksync_lite = ['0xccc'];
      selection.btc = ['bc1qaaa'];
      selection.solana = ['sol1'];
      await nextTick();

      expect(onAllSelected).toHaveBeenLastCalledWith(true);
    });
  });
});
