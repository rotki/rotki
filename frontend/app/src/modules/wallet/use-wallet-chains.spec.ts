import type { EvmChainInfo } from '@/modules/core/api/types/chains';
import { Blockchain } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useWalletChains } from '@/modules/wallet/use-wallet-chains';

// The seam: the wallet's chain list is whatever the backend reports, joined to
// the numeric EIP-155 ids, and never a hardcoded list. A chain the backend gains
// must show up with no frontend change; a chain that cannot be resolved to a
// numeric id must be dropped, not silently turned into ethereum.

function evmChain(id: string, evmChainName: string): EvmChainInfo {
  return { evmChainName, id, image: `${id}.svg`, name: id, type: 'evm' };
}

const txEvmChains = ref<EvmChainInfo[]>([]);
const allEvmChains = ref<{ id: number; label: string; name: string }[]>([]);

// `evmChainsData` is the wider list that still holds AVAX. It is here so that
// sourcing the wallet chains from it instead of `txEvmChains` fails a test
// rather than passing unnoticed.
const evmChainsData = computed<EvmChainInfo[]>(() => [
  ...get(txEvmChains),
  evmChain(Blockchain.AVAX, 'avalanche'),
]);

const getEvmChainId = vi.fn((name: string): number | undefined =>
  get(allEvmChains).find(item => item.name === name)?.id);

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn().mockImplementation(() => ({ evmChainsData, getEvmChainId, txEvmChains })),
}));

describe('useWalletChains', () => {
  beforeEach(() => {
    // Ordered as the backend serializes SupportedBlockchain, ethereum first.
    set(txEvmChains, [
      evmChain(Blockchain.ETH, 'ethereum'),
      evmChain(Blockchain.OPTIMISM, 'optimism'),
      evmChain(Blockchain.BASE, 'base'),
      evmChain(Blockchain.HYPERLIQUID, 'hyperliquid'),
      evmChain(Blockchain.MONAD, 'monad'),
    ]);
    set(allEvmChains, [
      { id: 1, label: 'Ethereum', name: 'ethereum' },
      { id: 10, label: 'Optimism', name: 'optimism' },
      { id: 8453, label: 'Base', name: 'base' },
      { id: 999, label: 'Hyperliquid', name: 'hyperliquid' },
      { id: 143, label: 'Monad', name: 'monad' },
      { id: 43114, label: 'Avalanche', name: 'avalanche' },
    ]);
  });

  it('should pair every chain the backend reports with its numeric id', () => {
    const { walletChains } = useWalletChains();

    expect(get(walletChains)).toEqual([
      { chain: Blockchain.ETH, chainId: 1 },
      { chain: Blockchain.OPTIMISM, chainId: 10 },
      { chain: Blockchain.BASE, chainId: 8453 },
      { chain: Blockchain.HYPERLIQUID, chainId: 999 },
      { chain: Blockchain.MONAD, chainId: 143 },
    ]);
  });

  it('should include a chain the backend has newly gained', () => {
    const { walletChainIds, walletChains } = useWalletChains();

    // The two chains the previously hardcoded list was missing.
    expect(get(walletChains).map(item => item.chain)).toContain(Blockchain.MONAD);
    expect(get(walletChainIds)).toContain(999);
  });

  it('should not offer a chain with no transaction support', () => {
    const { walletChains } = useWalletChains();

    // avalanche is an evm chain with a numeric id, so only the choice of
    // `txEvmChains` over `evmChainsData` keeps it out. A send finishes by
    // recording its hash, which avalanche cannot do.
    expect(get(evmChainsData).map(item => item.id)).toContain(Blockchain.AVAX);
    expect(get(walletChains).map(item => item.chain)).not.toContain(Blockchain.AVAX);
  });

  it('should drop a chain with no numeric id instead of defaulting it', () => {
    set(txEvmChains, [...get(txEvmChains), evmChain('newchain', 'newchain')]);
    const { walletChains } = useWalletChains();

    expect(get(walletChains).map(item => item.chain)).not.toContain('newchain');
    // The trap this guards: resolving it to 1 would label its balances ethereum.
    expect(get(walletChains).filter(item => item.chainId === 1)).toHaveLength(1);
  });

  it('should react to the chain list arriving after login', () => {
    const { walletChains } = useWalletChains();
    set(txEvmChains, []);
    expect(get(walletChains)).toEqual([]);

    set(txEvmChains, [evmChain(Blockchain.MONAD, 'monad')]);
    expect(get(walletChains)).toEqual([{ chain: Blockchain.MONAD, chainId: 143 }]);
  });

  describe('getSessionChains', () => {
    it('should offer every chain when the connection reports none', () => {
      const { getSessionChains, walletChains } = useWalletChains();

      expect(getSessionChains()).toHaveLength(get(walletChains).length);
      expect(getSessionChains([])).toHaveLength(get(walletChains).length);
    });

    it('should narrow to the chains the session reports', () => {
      const { getSessionChains } = useWalletChains();

      expect(getSessionChains([1, 143])).toEqual([Blockchain.ETH, Blockchain.MONAD]);
    });

    it('should drop a session chain rotki does not support', () => {
      const { getSessionChains } = useWalletChains();

      // 250 and 1284 are chains the backend never reported. Mapping each id to a
      // chain instead of intersecting resolved both to ethereum, which put
      // duplicate entries in the send form's chain picker.
      expect(getSessionChains([1, 250, 1284])).toEqual([Blockchain.ETH]);
    });

    it('should keep rotki ordering, not the order the session sent', () => {
      const { getSessionChains } = useWalletChains();

      expect(getSessionChains([143, 1])).toEqual([Blockchain.ETH, Blockchain.MONAD]);
    });
  });
});
