import type { ComputedRef, Ref } from 'vue';
import type { HistoricalBalancesResponse } from '@/modules/history/balances/types';
import type { TaskMeta } from '@/types/task';
import {
  type AssetBalanceWithPrice,
  type BigNumber,
  bigNumberify,
  Zero,
} from '@rotki/common';
import dayjs from 'dayjs';
import { useHistoricalBalancesApi } from '@/composables/api/balances/historical-balances-api';
import { summarizeAssetProtocols } from '@/composables/balances/asset-summary';
import { displayDateFormatter } from '@/data/date-formatter';
import { useCollectionInfo } from '@/modules/assets/use-collection-info';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useHistoricCachePriceStore } from '@/store/prices/historic';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

interface UseHistoricalBalancesReturn {
  balances: ComputedRef<AssetBalanceWithPrice[]>;
  errorMessage: Ref<string | undefined>;
  fetchBalances: () => Promise<void>;
  hasResults: ComputedRef<boolean>;
  loading: Ref<boolean>;
  noDataFound: ComputedRef<boolean>;
  queriedTimestamp: Ref<number | undefined>;
  selectedAsset: Ref<string | undefined>;
  selectedLocation: Ref<string>;
  selectedLocationLabel: Ref<string>;
  selectedProtocol: Ref<string | undefined>;
  timestamp: Ref<number>;
}

export function useHistoricalBalances(): UseHistoricalBalancesReturn {
  const timestamp = ref<number>(dayjs().unix());
  const selectedAsset = ref<string>();
  const selectedLocation = ref<string>('');
  const selectedLocationLabel = ref<string>('');
  const selectedProtocol = ref<string>();
  const rawEntries = ref<Record<string, string>>({});
  const loading = ref<boolean>(false);
  const errorMessage = ref<string>();
  const queriedTimestamp = ref<number>();
  const queryCompleted = ref<boolean>(false);

  const { t } = useI18n({ useScope: 'global' });

  const { fetchHistoricalBalances, processHistoricalBalances } = useHistoricalBalancesApi();
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { useCollectionId, useCollectionMainAsset } = useCollectionInfo();
  const { awaitTask } = useTaskStore();
  const { historicPriceInCurrentCurrency } = useHistoricCachePriceStore();
  const { dateDisplayFormat } = storeToRefs(useGeneralSettingsStore());

  const balances = computed<AssetBalanceWithPrice[]>(() => {
    const entries = get(rawEntries);
    const ts = get(queriedTimestamp);

    if (Object.keys(entries).length === 0 || !ts)
      return [];

    const sources: Record<string, Record<string, { amount: BigNumber; value: BigNumber }>> = {};
    const prices: Record<string, BigNumber> = {};

    for (const [asset, amountStr] of Object.entries(entries)) {
      const amount = bigNumberify(amountStr);
      const price = get(historicPriceInCurrentCurrency(asset, ts));
      prices[asset] = price.lt(0) ? Zero : price;
      const value = amount.multipliedBy(prices[asset]);

      sources[asset] = {
        historical: { amount, value },
      };

      // Also fetch price for collection main asset if this asset belongs to a collection
      const collectionId = get(useCollectionId(asset));
      if (collectionId) {
        const mainAsset = get(useCollectionMainAsset(collectionId));
        if (mainAsset && !prices[mainAsset]) {
          const price = get(historicPriceInCurrentCurrency(mainAsset, ts));
          prices[mainAsset] = price.lt(0) ? Zero : price;
        }
      }
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
        getAssetPrice: (asset: string) => prices[asset],
        noPrice: Zero,
      },
      {
        groupCollections: true,
        useCollectionId,
        useCollectionMainAsset,
      },
    );
  });

  const hasResults = computed<boolean>(() => get(balances).length > 0);
  const noDataFound = computed<boolean>(() => get(queryCompleted) && Object.keys(get(rawEntries)).length === 0);

  function formatTimestamp(ts: number): string {
    return displayDateFormatter.format(new Date(ts * 1000), get(dateDisplayFormat));
  }

  function getTaskDescription(ts: number, asset?: string): string {
    const formattedTime = formatTimestamp(ts);
    if (asset)
      return t('historical_balances.task_description_asset', { timestamp: formattedTime, asset });

    return t('historical_balances.task_description_all', { timestamp: formattedTime });
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

  async function queryBalances(ts: number, asset?: string, location?: string, locationLabel?: string, protocol?: string): Promise<HistoricalBalancesResponse> {
    const payload = {
      timestamp: ts,
      ...(asset ? { asset } : {}),
      ...(location ? { location } : {}),
      ...(locationLabel ? { locationLabel } : {}),
      ...(protocol ? { protocol } : {}),
    };

    const { taskId } = await fetchHistoricalBalances(payload);

    const { result } = await awaitTask<HistoricalBalancesResponse, TaskMeta>(
      taskId,
      TaskType.QUERY_HISTORICAL_BALANCES,
      {
        title: t('historical_balances.title'),
        description: getTaskDescription(ts, asset),
      },
    );

    return result;
  }

  async function fetchBalances(): Promise<void> {
    const ts = get(timestamp);
    const asset = get(selectedAsset);
    const location = get(selectedLocation) || undefined;
    const locationLabel = get(selectedLocationLabel) || undefined;
    const protocol = get(selectedProtocol);

    set(loading, true);
    set(errorMessage, undefined);
    set(rawEntries, {});
    set(queryCompleted, false);

    try {
      let result = await queryBalances(ts, asset, location, locationLabel, protocol);

      // Keep triggering processing until processing_required is false
      while (result.processingRequired) {
        await triggerProcessing();
        result = await queryBalances(ts, asset, location, locationLabel, protocol);
      }

      set(rawEntries, result.entries ?? {});
      set(queriedTimestamp, ts);
      set(loading, false);
      set(queryCompleted, true);
    }
    catch (error: any) {
      let errorMsg: string;
      if (error.message?.includes('404') || error.message?.includes('No historical data'))
        errorMsg = t('historical_balances.no_data');
      else
        errorMsg = error.message;

      set(errorMessage, errorMsg);
      set(loading, false);
    }
  }

  return {
    balances,
    errorMessage,
    fetchBalances,
    hasResults,
    loading,
    noDataFound,
    queriedTimestamp,
    selectedAsset,
    selectedLocation,
    selectedLocationLabel,
    selectedProtocol,
    timestamp,
  };
}
