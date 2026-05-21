import { get } from '@vueuse/core';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { type ChainAddress, TransactionChainType } from '@/modules/history/events/event-payloads';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

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
  const { disabledChainQueries } = storeToRefs(useGeneralSettingsStore());

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

  const filterDisabledChainAccounts = (accounts: ChainAddress[]): ChainAddress[] => {
    const disabled = get(disabledChainQueries);
    return accounts.filter(({ address, chain }) => {
      const rule = disabled[chain];
      if (rule === undefined)
        return true;
      // Backend contract: an empty rule array means the entire chain is disabled.
      if (rule.length === 0)
        return false;
      return !rule.includes(address);
    });
  };

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
