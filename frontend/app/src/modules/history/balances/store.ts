import type { HistoricalBalanceSource } from '@/modules/history/balances/types';
import type { HistoricalBalanceProcessingData, NegativeBalanceDetectedData } from '@/modules/messaging/types/status-types';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';

export interface SavedHistoricalBalancesFilters {
  timestamp: number;
  selectedAsset?: string;
  selectedLocation: string;
  selectedLocationLabel: string;
  selectedProtocol?: string;
  source: HistoricalBalanceSource;
  selectedAccount?: BlockchainAccount<AddressData>;
}

export const useHistoricalBalancesStore = defineStore('balances/historical', () => {
  const processingProgress = ref<HistoricalBalanceProcessingData>();
  const negativeBalances = ref<NegativeBalanceDetectedData[]>([]);

  // Saved filter state - only persisted when user clicks "Get Historical Balances"
  const savedFilters = ref<SavedHistoricalBalancesFilters>();

  const isProcessing = computed<boolean>(() => {
    const progress = get(processingProgress);
    return !!progress && progress.total > 0 && progress.processed < progress.total;
  });

  const processingPercentage = computed<number>(() => {
    const progress = get(processingProgress);
    if (!progress || progress.total === 0)
      return 0;
    return Math.round((progress.processed / progress.total) * 100);
  });

  function setProcessingProgress(data: HistoricalBalanceProcessingData): void {
    const current = get(processingProgress);

    // If processed count is lower than before, it means a new cycle started - reset negative balances
    if (current && data.processed < current.processed) {
      set(negativeBalances, []);
    }

    set(processingProgress, data);
  }

  function addNegativeBalance(data: NegativeBalanceDetectedData): void {
    const current = get(negativeBalances);

    // If the array is not empty and the lastRunTs is different, clear and start fresh
    if (current.length > 0 && current[0].lastRunTs !== data.lastRunTs) {
      set(negativeBalances, [data]);
      return;
    }

    // Accumulate the new data
    set(negativeBalances, [...current, data]);
  }

  function setSavedFilters(filters: SavedHistoricalBalancesFilters): void {
    set(savedFilters, filters);
  }

  return {
    addNegativeBalance,
    isProcessing,
    negativeBalances,
    processingPercentage,
    processingProgress,
    savedFilters,
    setProcessingProgress,
    setSavedFilters,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useHistoricalBalancesStore, import.meta.hot));
