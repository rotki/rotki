import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockFetchEthStakingValidators = vi.fn();

vi.mock('@/modules/staking/eth/composables/use-eth-validator-fetching', () => ({
  useEthValidatorFetching: vi.fn(() => ({
    fetchEthStakingValidators: mockFetchEthStakingValidators,
  })),
}));

const mockRefreshBlockchainBalances = vi.fn();

vi.mock('@/modules/balances/use-blockchain-balances', () => ({
  useBlockchainBalances: vi.fn(() => ({
    refreshBlockchainBalances: mockRefreshBlockchainBalances,
  })),
}));

const mockPremium = ref<boolean>(false);

vi.mock('@/composables/premium', () => ({
  usePremium: vi.fn(() => mockPremium),
}));

const mockIsEth2Enabled = vi.fn((): boolean => false);

vi.mock('@/store/blockchain/validators', () => ({
  useBlockchainValidatorsStore: vi.fn(() => ({
    isEth2Enabled: mockIsEth2Enabled,
  })),
}));

describe('useEthValidatorWatchers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(mockPremium, false);
    mockIsEth2Enabled.mockReturnValue(false);
  });

  it('should refresh validators and balances when premium changes and eth2 is enabled', async () => {
    mockIsEth2Enabled.mockReturnValue(true);
    mockFetchEthStakingValidators.mockResolvedValue(undefined);
    mockRefreshBlockchainBalances.mockResolvedValue(undefined);

    const { useEthValidatorWatchers } = await import(
      '@/modules/staking/eth/composables/use-eth-validator-watchers',
    );
    useEthValidatorWatchers();

    set(mockPremium, true);
    await nextTick();
    await flushPromises();

    expect(mockFetchEthStakingValidators).toHaveBeenCalledWith({ ignoreCache: true });
    expect(mockRefreshBlockchainBalances).toHaveBeenCalledWith({
      blockchain: 'eth2',
    });
  });

  it('should not refresh when eth2 is not enabled', async () => {
    const { useEthValidatorWatchers } = await import(
      '@/modules/staking/eth/composables/use-eth-validator-watchers',
    );
    useEthValidatorWatchers();

    set(mockPremium, true);
    await nextTick();
    await flushPromises();

    expect(mockFetchEthStakingValidators).not.toHaveBeenCalled();
    expect(mockRefreshBlockchainBalances).not.toHaveBeenCalled();
  });
});
