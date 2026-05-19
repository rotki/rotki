import type { RecentTransaction } from '@/modules/wallet/types';
import { Blockchain } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useWalletHelper } from '@/modules/wallet/use-wallet-helper';

function makeRecentTx(overrides: Partial<RecentTransaction> = {}): RecentTransaction {
  return {
    chain: Blockchain.ETH,
    context: '',
    hash: '0x0',
    initiatorAddress: '0x0',
    metadata: undefined,
    status: 'pending',
    timestamp: 0,
    ...overrides,
  };
}

const allEvmChains = ref<{ id: number; name: string }[]>([
  { id: 1, name: 'ethereum' },
  { id: 10, name: 'optimism' },
  { id: 42161, name: 'arbitrum_one' },
]);

const getChain = vi.fn((name: string): Blockchain => {
  if (name === 'optimism')
    return Blockchain.OPTIMISM;
  if (name === 'arbitrum_one')
    return Blockchain.ARBITRUM_ONE;
  return Blockchain.ETH;
});

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn().mockImplementation(() => ({ allEvmChains, getChain })),
}));

const refreshBlockchainBalances = vi.fn();
const addTransactionHash = vi.fn();

vi.mock('@/modules/balances/use-blockchain-balances', () => ({
  useBlockchainBalances: vi.fn().mockImplementation(() => ({ refreshBlockchainBalances })),
}));

vi.mock('@/modules/history/events/tx/use-history-transactions', () => ({
  useHistoryTransactions: vi.fn().mockImplementation(() => ({ addTransactionHash })),
}));

describe('useWalletHelper', () => {
  beforeEach(() => {
    refreshBlockchainBalances.mockReset().mockResolvedValue(undefined);
    addTransactionHash.mockReset().mockResolvedValue(undefined);
    getChain.mockClear();
  });

  describe('getEvmChainNameFromChainId', () => {
    it('should return matching chain name for known numeric id', () => {
      const { getEvmChainNameFromChainId } = useWalletHelper();
      expect(getEvmChainNameFromChainId(10)).toBe('optimism');
    });

    it('should handle bigint chainId', () => {
      const { getEvmChainNameFromChainId } = useWalletHelper();
      expect(getEvmChainNameFromChainId(42161n)).toBe('arbitrum_one');
    });

    it('should fall back to ethereum for unknown chainId', () => {
      const { getEvmChainNameFromChainId } = useWalletHelper();
      expect(getEvmChainNameFromChainId(99999)).toBe('ethereum');
    });
  });

  describe('getChainFromChainId', () => {
    it('should map chainId to a Blockchain via getChain', () => {
      const { getChainFromChainId } = useWalletHelper();
      const result = getChainFromChainId(10);
      expect(getChain).toHaveBeenCalledWith('optimism');
      expect(result).toBe(Blockchain.OPTIMISM);
    });
  });

  describe('getChainIdFromChain', () => {
    it('should return numeric id for known chain', () => {
      const { getChainIdFromChain } = useWalletHelper();
      expect(getChainIdFromChain('arbitrum_one')).toBe(42161);
    });

    it('should default to 1 for unknown chain', () => {
      const { getChainIdFromChain } = useWalletHelper();
      expect(getChainIdFromChain('nope')).toBe(1);
    });
  });

  describe('getEip155ChainId / getChainIdFromNamespace', () => {
    it('should round-trip an eip155 chain id', () => {
      const { getEip155ChainId, getChainIdFromNamespace } = useWalletHelper();

      expect(getEip155ChainId(10)).toBe('eip155:10');
      expect(getEip155ChainId('42161')).toBe('eip155:42161');
      expect(getChainIdFromNamespace('eip155:10')).toBe(10);
      expect(getChainIdFromNamespace(getEip155ChainId(42161))).toBe(42161);
    });
  });

  describe('updateStatePostTransaction', () => {
    it('should do nothing when tx is undefined', async () => {
      const { updateStatePostTransaction } = useWalletHelper();
      await updateStatePostTransaction(undefined);

      expect(refreshBlockchainBalances).not.toHaveBeenCalled();
      expect(addTransactionHash).not.toHaveBeenCalled();
    });

    it('should refresh balances and register the transaction hash', async () => {
      const { updateStatePostTransaction } = useWalletHelper();
      await updateStatePostTransaction(makeRecentTx({
        chain: Blockchain.OPTIMISM,
        hash: '0xabc',
        initiatorAddress: '0xinit',
      }));

      expect(refreshBlockchainBalances).toHaveBeenCalledWith({ blockchain: Blockchain.OPTIMISM });
      expect(addTransactionHash).toHaveBeenCalledWith({
        associatedAddress: '0xinit',
        blockchain: Blockchain.OPTIMISM,
        txRef: '0xabc',
      });
    });
  });
});
