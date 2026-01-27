import type { RepullingTransactionPayload } from '@/types/history/events';
import { createSharedComposable, get, useArrayMap } from '@vueuse/core';
import dayjs from 'dayjs';
import { computed, type ComputedRef } from 'vue';
import { useSupportedChains } from '@/composables/info/chains';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';

export const SECONDS_PER_DAY = 24 * 60 * 60;

/**
 * Threshold for showing confirmation dialog before repulling transactions.
 * Calculated as: number of accounts × number of days.
 * e.g., 1825 = 1 account for ~5 years, or 5 accounts for ~1 year.
 */
export const CONFIRMATION_THRESHOLD = 1825;

export const EXCHANGES_WITHOUT_DATE_RANGE_FILTER: string[] = [
  'coinbase',
  'binance',
  'binanceus',
  'bitmex',
];

export function shouldShowDateRangePicker(
  isBlockchainType: boolean,
  exchange: { location: string } | undefined,
): boolean {
  if (isBlockchainType)
    return true;

  if (!exchange)
    return true;

  return !EXCHANGES_WITHOUT_DATE_RANGE_FILTER.includes(exchange.location);
}

export function getTimeRangeInDays(data: RepullingTransactionPayload): number {
  if (!data.fromTimestamp || !data.toTimestamp)
    return 0;

  return Math.ceil((data.toTimestamp - data.fromTimestamp) / SECONDS_PER_DAY);
}

interface UseRepullingTransactionFormReturn {
  chainOptions: ComputedRef<string[]>;
  createDefaultFormData: () => RepullingTransactionPayload;
  getUsableChains: (chain: string | undefined) => string[];
  shouldShowConfirmation: (data: RepullingTransactionPayload) => boolean;
}

function useRepullingTransactionFormFn(): UseRepullingTransactionFormReturn {
  const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());
  const { decodableTxChainsInfo, getChain } = useSupportedChains();
  const decodableTxChains = useArrayMap(decodableTxChainsInfo, x => x.id);

  const chainOptions = computed<string[]>(() => {
    const decodableChains = get(decodableTxChains);
    const chains = Object.entries(get(accountsPerChain))
      .filter(([chain, accounts]) => accounts.length > 0 && decodableChains.includes(chain))
      .map(([chain]) => chain);

    if (chains.length > 0)
      return ['all', ...chains];

    return chains;
  });

  function createDefaultFormData(): RepullingTransactionPayload {
    return {
      address: '',
      chain: 'all',
      fromTimestamp: dayjs().subtract(1, 'year').unix(),
      toTimestamp: dayjs().unix(),
    };
  }

  function getUsableChains(chain: string | undefined): string[] {
    if (!chain || chain === 'all')
      return get(chainOptions).filter(c => c !== 'all');

    return [getChain(chain)];
  }

  function getAffectedAccountsCount(data: RepullingTransactionPayload): number {
    const accountsPerChainVal = get(accountsPerChain);
    const chainOptionsVal = get(chainOptions);

    if (data.chain && data.chain !== 'all') {
      if (data.address)
        return 1;

      return accountsPerChainVal[data.chain]?.length ?? 0;
    }

    return chainOptionsVal
      .filter(chain => chain !== 'all')
      .reduce((total, chain) => total + (accountsPerChainVal[chain]?.length ?? 0), 0);
  }

  function shouldShowConfirmation(data: RepullingTransactionPayload): boolean {
    const accountsCount = getAffectedAccountsCount(data);
    const daysCount = getTimeRangeInDays(data);

    return accountsCount * daysCount > CONFIRMATION_THRESHOLD;
  }

  return {
    chainOptions,
    createDefaultFormData,
    getUsableChains,
    shouldShowConfirmation,
  };
}

export const useRepullingTransactionForm = createSharedComposable(useRepullingTransactionFormFn);
