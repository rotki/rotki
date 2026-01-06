import type { HistoricalBalanceProcessingData, NegativeBalanceDetectedData } from '@/modules/messaging/types/status-types';
import type { TaskMeta } from '@/types/task';
import { useHistoricalBalancesApi } from '@/composables/api/balances/historical-balances-api';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

export const useHistoricalBalancesStore = defineStore('balances/historical', () => {
  const processingProgress = ref<HistoricalBalanceProcessingData>();
  const negativeBalances = ref<NegativeBalanceDetectedData[]>([]);

  const { t } = useI18n({ useScope: 'global' });

  const { processHistoricalBalances } = useHistoricalBalancesApi();
  const { awaitTask } = useTaskStore();

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

  async function triggerProcessing(): Promise<void> {
    const { taskId } = await processHistoricalBalances();

    await awaitTask<boolean, TaskMeta>(
      taskId,
      TaskType.PROCESS_HISTORICAL_BALANCES,
      {
        title: t('historical_balances.title'),
        description: t('historical_balances.processing_description'),
      },
    );
  }

  return {
    addNegativeBalance,
    isProcessing,
    negativeBalances,
    processingPercentage,
    processingProgress,
    setProcessingProgress,
    triggerProcessing,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useHistoricalBalancesStore, import.meta.hot));
