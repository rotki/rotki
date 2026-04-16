import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockEvmChains = ref([
  { evmChainName: 'Ethereum', id: 'eth', image: '', name: 'Ethereum', type: 'evm' as const },
  { evmChainName: 'Optimism', id: 'optimism', image: '', name: 'Optimism', type: 'evm' as const },
  { evmChainName: 'Polygon POS', id: 'polygon_pos', image: '', name: 'Polygon POS', type: 'evm' as const },
]);

const mockAddresses = ref<Record<string, string[]>>({
  eth: ['0xaddr1'],
  optimism: ['0xaddr2'],
});

const mockIsTaskRunning = vi.fn().mockReturnValue(false);
const mockUseIsTaskRunning = vi.fn().mockReturnValue(computed(() => false));
const mockMassDetectTokens = vi.fn().mockResolvedValue(undefined);

vi.mock('@/modules/core/tasks/use-task-store', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    isTaskRunning: (...args: unknown[]): boolean => mockIsTaskRunning(...args),
    useIsTaskRunning: (...args: unknown[]): unknown => mockUseIsTaskRunning(...args),
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn().mockReturnValue({
    txEvmChains: mockEvmChains,
  }),
}));

vi.mock('@/modules/balances/blockchain/use-account-addresses', () => ({
  useAccountAddresses: vi.fn().mockReturnValue({
    addresses: mockAddresses,
  }),
}));

vi.mock('@/modules/balances/use-balance-refresh', () => ({
  useBalanceRefresh: vi.fn().mockReturnValue({
    massDetectTokens: async (...args: unknown[]): Promise<void> => mockMassDetectTokens(...args),
  }),
}));

const { useDetectTokenChainsSelection } = await import('./use-detect-token-chains-selection');

describe('useDetectTokenChainsSelection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsTaskRunning.mockReturnValue(false);
    set(mockAddresses, {
      eth: ['0xaddr1'],
      optimism: ['0xaddr2'],
    });
  });

  describe('filtered', () => {
    it('should only include chains with accounts', () => {
      const search = ref<string>('');
      const { filtered } = useDetectTokenChainsSelection(search);

      // polygon_pos has no accounts
      expect(get(filtered).map(c => c.id)).toEqual(['eth', 'optimism']);
    });

    it('should filter by search query', () => {
      const search = ref<string>('opti');
      const { filtered } = useDetectTokenChainsSelection(search);

      expect(get(filtered).map(c => c.id)).toEqual(['optimism']);
    });

    it('should return all chains with accounts when search is empty', () => {
      const search = ref<string>('');
      const { filtered } = useDetectTokenChainsSelection(search);

      expect(get(filtered)).toHaveLength(2);
    });

    it('should return empty when no chains match search', () => {
      const search = ref<string>('solana');
      const { filtered } = useDetectTokenChainsSelection(search);

      expect(get(filtered)).toHaveLength(0);
    });

    it('should react to address changes', () => {
      const search = ref<string>('');
      const { filtered } = useDetectTokenChainsSelection(search);

      expect(get(filtered)).toHaveLength(2);

      set(mockAddresses, { eth: ['0xaddr1'] });

      expect(get(filtered)).toHaveLength(1);
      expect(get(filtered)[0].id).toBe('eth');
    });
  });

  describe('toggle', () => {
    it('should select a chain when toggled on', () => {
      const { isSelected, toggle } = useDetectTokenChainsSelection('');

      toggle('eth');

      expect(isSelected('eth')).toBe(true);
      expect(isSelected('optimism')).toBe(false);
    });

    it('should deselect a chain when toggled off', () => {
      const { isSelected, toggle } = useDetectTokenChainsSelection('');

      toggle('eth');
      toggle('eth');

      expect(isSelected('eth')).toBe(false);
    });

    it('should select all filtered chains when called without arguments', () => {
      const { isSelected, toggle } = useDetectTokenChainsSelection('');

      toggle();

      expect(isSelected('eth')).toBe(true);
      expect(isSelected('optimism')).toBe(true);
    });

    it('should deselect all when called without arguments and all are selected', () => {
      const { hasSelection, toggle } = useDetectTokenChainsSelection('');

      toggle(); // select all
      toggle(); // deselect all

      expect(get(hasSelection)).toBe(false);
    });

    it('should not toggle a chain when detection is running for it', () => {
      mockIsTaskRunning.mockReturnValue(true);
      const { isSelected, toggle } = useDetectTokenChainsSelection('');

      toggle('eth');

      expect(isSelected('eth')).toBe(false);
    });

    it('should not toggle all when detection is running globally', () => {
      mockIsTaskRunning.mockReturnValue(true);
      const { hasSelection, toggle } = useDetectTokenChainsSelection('');

      toggle();

      expect(get(hasSelection)).toBe(false);
    });
  });

  describe('selection state', () => {
    it('should report correct selectedCount', () => {
      const { selectedCount, toggle } = useDetectTokenChainsSelection('');

      expect(get(selectedCount)).toBe(0);
      toggle('eth');
      expect(get(selectedCount)).toBe(1);
      toggle('optimism');
      expect(get(selectedCount)).toBe(2);
    });

    it('should report hasSelection correctly', () => {
      const { hasSelection, toggle } = useDetectTokenChainsSelection('');

      expect(get(hasSelection)).toBe(false);
      toggle('eth');
      expect(get(hasSelection)).toBe(true);
    });

    it('should report isAllSelected correctly', () => {
      const { isAllSelected, toggle } = useDetectTokenChainsSelection('');

      expect(get(isAllSelected)).toBe(false);
      toggle('eth');
      expect(get(isAllSelected)).toBe(false);
      toggle('optimism');
      expect(get(isAllSelected)).toBe(true);
    });
  });

  describe('reset', () => {
    it('should clear all selections', () => {
      const { hasSelection, reset, toggle } = useDetectTokenChainsSelection('');

      toggle('eth');
      toggle('optimism');
      expect(get(hasSelection)).toBe(true);

      reset();
      expect(get(hasSelection)).toBe(false);
    });
  });

  describe('detectChains', () => {
    it('should detect a single chain and return false', async () => {
      const { detectChains } = useDetectTokenChainsSelection('');

      const result = await detectChains('eth');

      expect(result).toBe(false);
      expect(mockMassDetectTokens).toHaveBeenCalledWith(['eth']);
    });

    it('should detect selected chains and return false when not all selected', async () => {
      const { detectChains, toggle } = useDetectTokenChainsSelection('');

      toggle('eth');
      const result = await detectChains();

      expect(result).toBe(false);
      expect(mockMassDetectTokens).toHaveBeenCalledWith(['eth']);
    });

    it('should return true without calling massDetectTokens when all chains are selected', async () => {
      const { detectChains, toggle } = useDetectTokenChainsSelection('');

      toggle(); // select all
      const result = await detectChains();

      expect(result).toBe(true);
      expect(mockMassDetectTokens).not.toHaveBeenCalled();
    });
  });
});
