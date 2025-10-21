import { get } from '@vueuse/core';
import { useSupportedChains } from '@/composables/info/chains';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { type ChainAddress, TransactionChainType } from '@/types/history/events';

interface UseHistoryTransactionAccountsReturn {
  getAllAccounts: (chains?: string[]) => ChainAddress[];
  getBitcoinAccounts: (chains?: string[]) => ChainAddress[];
  getEvmAccounts: (chains?: string[]) => ChainAddress[];
  getEvmLikeAccounts: (chains?: string[]) => ChainAddress[];
  getSolanaAccounts: (chains?: string[]) => ChainAddress[];
  getTransactionTypeFromChain: (chain: string) => TransactionChainType;
}

export function useHistoryTransactionAccounts(): UseHistoryTransactionAccountsReturn {
  const { addresses } = useAccountAddresses();
  const { isBtcChains, isEvmLikeChains, isSolanaChains, supportsTransactions } = useSupportedChains();

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

  const getSolanaAccounts = (chains: string[] = []): ChainAddress[] =>
    getAccountsByChainType(isSolanaChains, chains);

  const getAllAccounts = (chains: string[] = []): ChainAddress[] => [
    ...getEvmAccounts(chains),
    ...getEvmLikeAccounts(chains),
    ...getBitcoinAccounts(chains),
    ...getSolanaAccounts(chains),
  ];

  const getTransactionTypeFromChain = (chain: string): TransactionChainType => {
    if (isEvmLikeChains(chain))
      return TransactionChainType.EVMLIKE;
    if (isBtcChains(chain))
      return TransactionChainType.BITCOIN;
    if (isSolanaChains(chain))
      return TransactionChainType.SOLANA;

    return TransactionChainType.EVM;
  };

  return {
    getAllAccounts,
    getBitcoinAccounts,
    getEvmAccounts,
    getEvmLikeAccounts,
    getSolanaAccounts,
    getTransactionTypeFromChain,
  };
}
