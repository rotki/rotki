import { get } from '@vueuse/core';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { type ChainAddress, TransactionChainType } from '@/modules/history/events/event-payloads';
import { useDisabledChains } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chains';

interface UseHistoryTransactionAccountsReturn {
  filterDisabledChainAccounts: (accounts: ChainAddress[]) => ChainAddress[];
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
  const { filterAccounts } = useDisabledChains();

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

  // Kept as a named member of this composable because `use-refresh-transactions` calls it at a
  // deliberate point in the flow (before novelty detection), which the call site documents.
  const filterDisabledChainAccounts = (accounts: ChainAddress[]): ChainAddress[] =>
    filterAccounts(accounts);

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
    filterDisabledChainAccounts,
    getAllAccounts,
    getBitcoinAccounts,
    getEvmAccounts,
    getEvmLikeAccounts,
    getSolanaAccounts,
    getTransactionTypeFromChain,
  };
}
