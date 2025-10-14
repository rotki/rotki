import type { ChainAddress } from '@/types/history/events';
import { useSupportedChains } from '@/composables/info/chains';

interface CategorizedAccounts {
  evmAccounts: ChainAddress[];
  evmLikeAccounts: ChainAddress[];
  bitcoinAccounts: ChainAddress[];
  solanaAccounts: ChainAddress[];
}

interface UseAccountCategorizationReturn {
  categorizeAccountsByType: (accounts: ChainAddress[]) => CategorizedAccounts;
}

export function useAccountCategorization(): UseAccountCategorizationReturn {
  const { isBtcChains, isEvmLikeChains, isSolanaChains } = useSupportedChains();

  const categorizeAccountsByType = (accounts: ChainAddress[]): CategorizedAccounts => {
    const evmAccounts: ChainAddress[] = [];
    const evmLikeAccounts: ChainAddress[] = [];
    const bitcoinAccounts: ChainAddress[] = [];
    const solanaAccounts: ChainAddress[] = [];

    accounts.forEach((account) => {
      if (isEvmLikeChains(account.chain))
        evmLikeAccounts.push(account);
      else if (isBtcChains(account.chain))
        bitcoinAccounts.push(account);
      else if (isSolanaChains(account.chain))
        solanaAccounts.push(account);
      else
        evmAccounts.push(account);
    });

    return { bitcoinAccounts, evmAccounts, evmLikeAccounts, solanaAccounts };
  };

  return {
    categorizeAccountsByType,
  };
}
