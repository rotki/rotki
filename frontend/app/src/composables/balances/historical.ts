import type { ComputedRef, Ref, WritableComputedRef } from 'vue';
import type {
  HistoricalAssetBalance,
  HistoricalBalancesAllAssetsResponse,
  HistoricalBalancesProcessingRequiredResponse,
  HistoricalBalancesSingleAssetResponse,
} from '@/types/balances';
import type { TaskMeta } from '@/types/task';
import { type AssetBalanceWithPrice, type BigNumber, bigNumberify, NoPrice, NotificationGroup, Severity } from '@rotki/common';
import { createSharedComposable } from '@vueuse/core';
import dayjs from 'dayjs';
import { useHistoricalBalancesApi } from '@/composables/api/balances/historical-balances-api';
import { summarizeAssetProtocols } from '@/composables/balances/asset-summary';
import { displayDateFormatter } from '@/data/date-formatter';
import { useCollectionInfo } from '@/modules/assets/use-collection-info';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useNotificationsStore } from '@/store/notifications';
import { useAreaVisibilityStore } from '@/store/session/visibility';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

type HistoricalBalancesResponse =
  | HistoricalBalancesAllAssetsResponse
  | HistoricalBalancesSingleAssetResponse
  | HistoricalBalancesProcessingRequiredResponse;

interface HistoricalBalancesState {
  timestamp: number;
  asset?: string;
  balances: AssetBalanceWithPrice[];
  loading: boolean;
  errorMessage?: string;
  taskId?: number;
}

function defaultState(): HistoricalBalancesState {
  return {
    timestamp: dayjs().unix(),
    asset: undefined,
    balances: [],
    loading: false,
    errorMessage: undefined,
    taskId: undefined,
  };
}

interface UseHistoricalBalancesReturn {
  dialogOpen: Ref<boolean>;
  timestamp: WritableComputedRef<number>;
  selectedAsset: WritableComputedRef<string | undefined>;
  balances: ComputedRef<AssetBalanceWithPrice[]>;
  loading: ComputedRef<boolean>;
  errorMessage: ComputedRef<string | undefined>;
  hasResults: ComputedRef<boolean>;
  fetchBalances: () => Promise<void>;
  openDialog: () => void;
  closeDialog: () => void;
}

export const useHistoricalBalances = createSharedComposable((): UseHistoricalBalancesReturn => {
  const state = ref<HistoricalBalancesState>(defaultState());
  const { t } = useI18n({ useScope: 'global' });

  const { fetchHistoricalBalances, processHistoricalBalances } = useHistoricalBalancesApi();
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { useCollectionId, useCollectionMainAsset } = useCollectionInfo();
  const { awaitTask, useIsTaskRunning } = useTaskStore();
  const { notify, removeMatching } = useNotificationsStore();
  const { showHistoricalBalancesDialog } = storeToRefs(useAreaVisibilityStore());
  const { dateDisplayFormat } = storeToRefs(useGeneralSettingsStore());

  const isQueryTaskRunning = useIsTaskRunning(TaskType.QUERY_HISTORICAL_BALANCES);
  const isProcessTaskRunning = useIsTaskRunning(TaskType.PROCESS_HISTORICAL_BALANCES);

  const timestamp = computed<number>({
    get: () => get(state).timestamp,
    set: (value: number) => {
      set(state, { ...get(state), timestamp: value });
    },
  });

  const selectedAsset = computed<string | undefined>({
    get: () => get(state).asset,
    set: (value: string | undefined) => {
      set(state, { ...get(state), asset: value });
    },
  });

  const balances = computed<AssetBalanceWithPrice[]>(() => get(state).balances);
  const loading = computed<boolean>(() => get(state).loading);
  const errorMessage = computed<string | undefined>(() => get(state).errorMessage);
  const hasResults = computed<boolean>(() => get(state).balances.length > 0);
  const hasPendingTask = computed<boolean>(() => {
    const taskId = get(state).taskId;
    return taskId !== undefined && (get(isQueryTaskRunning) || get(isProcessTaskRunning));
  });

  function transformToAssetBalances(entries: Record<string, HistoricalAssetBalance>): AssetBalanceWithPrice[] {
    const sources: Record<string, Record<string, { amount: BigNumber; value: BigNumber }>> = {};

    for (const [asset, balance] of Object.entries(entries)) {
      const amount = bigNumberify(balance.amount);
      const price = bigNumberify(balance.price);
      const value = amount.multipliedBy(price);

      sources[asset] = {
        historical: { amount, value },
      };
    }

    return summarizeAssetProtocols(
      {
        associatedAssets: {},
        sources: { historical: sources },
      },
      {
        hideIgnored: false,
        isAssetIgnored,
      },
      {
        getAssetPrice: (asset: string) => {
          const balance = entries[asset];
          return balance ? bigNumberify(balance.price) : NoPrice;
        },
        noPrice: NoPrice,
      },
      {
        groupCollections: true,
        useCollectionId,
        useCollectionMainAsset,
      },
    );
  }

  function formatTimestamp(ts: number): string {
    return displayDateFormatter.format(new Date(ts * 1000), get(dateDisplayFormat));
  }

  function getTaskDescription(ts: number, asset?: string): string {
    const formattedTime = formatTimestamp(ts);
    if (asset)
      return t('historical_balances_dialog.task_description_asset', { timestamp: formattedTime, asset });

    return t('historical_balances_dialog.task_description_all', { timestamp: formattedTime });
  }

  async function triggerProcessing(): Promise<void> {
    const { taskId } = await processHistoricalBalances();

    set(state, { ...get(state), taskId });

    await awaitTask<boolean, TaskMeta>(
      taskId,
      TaskType.PROCESS_HISTORICAL_BALANCES,
      {
        title: t('historical_balances_dialog.title'),
        description: t('historical_balances_dialog.processing_description'),
      },
    );
  }

  async function queryBalances(ts: number, asset?: string): Promise<HistoricalBalancesResponse> {
    const payload = {
      timestamp: ts,
      ...(asset ? { asset } : {}),
    };

    const { taskId } = await fetchHistoricalBalances(payload);

    set(state, { ...get(state), taskId });

    const { result } = await awaitTask<HistoricalBalancesResponse, TaskMeta>(
      taskId,
      TaskType.QUERY_HISTORICAL_BALANCES,
      {
        title: t('historical_balances_dialog.title'),
        description: getTaskDescription(ts, asset),
      },
    );

    return result;
  }

  async function fetchBalances(): Promise<void> {
    const currentState = get(state);
    const ts = currentState.timestamp;
    const asset = currentState.asset;

    set(state, {
      ...currentState,
      loading: true,
      errorMessage: undefined,
      balances: [],
    });

    const taskDescription = getTaskDescription(ts, asset);

    try {
      let result = await queryBalances(ts, asset);

      if (result.processingRequired) {
        await triggerProcessing();
        result = await queryBalances(ts, asset);
      }

      if (result.processingRequired) {
        throw new Error(t('historical_balances_dialog.processing_failed'));
      }

      let entriesAsRecord: Record<string, HistoricalAssetBalance>;
      if (asset) {
        entriesAsRecord = { [asset]: result.entries as HistoricalAssetBalance };
      }
      else {
        entriesAsRecord = result.entries as Record<string, HistoricalAssetBalance>;
      }

      const transformedBalances = transformToAssetBalances(entriesAsRecord);

      set(state, {
        ...get(state),
        balances: transformedBalances,
        loading: false,
        taskId: undefined,
      });

      if (!get(showHistoricalBalancesDialog)) {
        notify({
          title: t('historical_balances_dialog.title'),
          message: taskDescription,
          severity: Severity.INFO,
          display: true,
          group: NotificationGroup.HISTORICAL_BALANCES,
          action: {
            label: t('historical_balances_dialog.view_results'),
            action: openDialog,
          },
        });
      }
    }
    catch (error: any) {
      let errorMsg: string;
      if (error.message?.includes('404') || error.message?.includes('No historical data'))
        errorMsg = t('historical_balances_dialog.no_data');
      else
        errorMsg = error.message;

      set(state, {
        ...get(state),
        errorMessage: errorMsg,
        loading: false,
        taskId: undefined,
      });

      if (!get(showHistoricalBalancesDialog)) {
        notify({
          title: t('historical_balances_dialog.title'),
          message: `${taskDescription}: ${errorMsg}`,
          severity: Severity.ERROR,
          display: true,
        });
      }
    }
  }

  function reset(): void {
    if (get(hasPendingTask) || get(hasResults))
      return;

    set(state, defaultState());
  }

  function dismissNotification(): void {
    removeMatching(notification => notification.group === NotificationGroup.HISTORICAL_BALANCES);
  }

  function openDialog(): void {
    dismissNotification();
    set(showHistoricalBalancesDialog, true);
  }

  function closeDialog(): void {
    set(showHistoricalBalancesDialog, false);
    reset();
  }

  return {
    dialogOpen: showHistoricalBalancesDialog,
    timestamp,
    selectedAsset,
    balances,
    loading,
    errorMessage,
    hasResults,
    fetchBalances,
    openDialog,
    closeDialog,
  };
});
