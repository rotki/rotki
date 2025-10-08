import type { ChainAddress } from '@/types/history/events';
import { get } from '@vueuse/core';
import { useSupportedChains } from '@/composables/info/chains';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';

interface UseHistoryTransactionAccountsReturn {
  getEvmAccounts: (chains?: string[]) => ChainAddress[];
  getEvmLikeAccounts: (chains?: string[]) => ChainAddress[];
  getBitcoinAccounts: (chains?: string[]) => ChainAddress[];
}

export function useHistoryTransactionAccounts(): UseHistoryTransactionAccountsReturn {
  const { addresses } = useAccountAddresses();
  const { isBtcChains, isEvmLikeChains, supportsTransactions } = useSupportedChains();

  const getAccountsByChainType = (
    chainFilter: (chain: string) => boolean,
    chains: string[] = [],
  ): ChainAddress[] =>
    Object.entries(get(addresses))
      .filter(([chain]) => chainFilter(chain) && (chains.length === 0 || chains.includes(chain)))
      .flatMap(([chain, addresses]) =>
        addresses.map(address => ({
          address,
          chain,
        })),
      );

  const getEvmAccounts = (chains: string[] = []): ChainAddress[] =>
    getAccountsByChainType(supportsTransactions, chains);

  const getEvmLikeAccounts = (chains: string[] = []): ChainAddress[] =>
    getAccountsByChainType(isEvmLikeChains, chains);

  const getBitcoinAccounts = (chains: string[] = []): ChainAddress[] =>
    getAccountsByChainType(isBtcChains, chains);

  return {
    getBitcoinAccounts,
    getEvmAccounts,
    getEvmLikeAccounts,
  };
}
