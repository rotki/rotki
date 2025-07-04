import type { BitcoinChainAddress, EvmChainAddress } from '@/types/history/events';
import { useSupportedChains } from '@/composables/info/chains';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { get } from '@vueuse/core';

interface UseHistoryTransactionAccountsReturn {
  getEvmAccounts: (chains?: string[]) => EvmChainAddress[];
  getEvmLikeAccounts: (chains?: string[]) => EvmChainAddress[];
  getBitcoinAccounts: (chains?: string[]) => BitcoinChainAddress[];
}

export function useHistoryTransactionAccounts(): UseHistoryTransactionAccountsReturn {
  const { addresses } = useAccountAddresses();
  const { getEvmChainName, isBtcChains, isEvmLikeChains, supportsTransactions } = useSupportedChains();

  const getEvmAccounts = (chains: string[] = []): EvmChainAddress[] =>
    Object.entries(get(addresses))
      .filter(([chain]) => supportsTransactions(chain) && (chains.length === 0 || chains.includes(chain)))
      .flatMap(([chain, addresses]) => {
        const evmChain = getEvmChainName(chain) ?? '';
        return addresses.map(address => ({
          address,
          evmChain,
        }));
      });

  const getEvmLikeAccounts = (chains: string[] = []): EvmChainAddress[] =>
    Object.entries(get(addresses))
      .filter(([chain]) => isEvmLikeChains(chain) && (chains.length === 0 || chains.includes(chain)))
      .flatMap(([evmChain, addresses]) =>
        addresses.map(address => ({
          address,
          evmChain,
        })),
      );

  const getBitcoinAccounts = (chains: string[] = []): BitcoinChainAddress[] =>
    Object.entries(get(addresses))
      .filter(([chain]) => isBtcChains(chain) && (chains.length === 0 || chains.includes(chain)))
      .flatMap(([chain, addresses]) =>
        addresses.map(address => ({
          address,
          chain,
        })),
      );

  return {
    getBitcoinAccounts,
    getEvmAccounts,
    getEvmLikeAccounts,
  };
}
