import type { ComputedRef, Ref } from 'vue';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { TaskMeta } from '@/types/task';
import {
  type AssetBalanceWithPrice,
  type BigNumber,
  Zero,
} from '@rotki/common';
import dayjs from 'dayjs';
import { useHistoricalBalancesApi } from '@/composables/api/balances/historical-balances-api';
import { summarizeAssetProtocols } from '@/composables/balances/asset-summary';
import { useSupportedChains } from '@/composables/info/chains';
import { displayDateFormatter } from '@/data/date-formatter';
import { useCollectionInfo } from '@/modules/assets/use-collection-info';
import { useHistoricalBalancesStore } from '@/modules/history/balances/store';
import {
  type HistoricalBalanceSource,
  HistoricalBalancesResponse,
  OnchainHistoricalBalanceResponse,
  HistoricalBalanceSource as Source,
} from '@/modules/history/balances/types';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useHistoricCachePriceStore } from '@/store/prices/historic';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTaskStore } from '@/store/tasks';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import { TaskType } from '@/types/task-type';

interface UseHistoricalBalancesReturn {
  balances: ComputedRef<AssetBalanceWithPrice[]>;
  errorMessage: Ref<string | undefined>;
  fetchBalances: () => Promise<void>;
  fieldErrors: Ref<ValidationErrors>;
  hasResults: ComputedRef<boolean>;
  hasSavedFilters: ComputedRef<boolean>;
  loading: Ref<boolean>;
  noDataFound: ComputedRef<boolean>;
  queriedTimestamp: Ref<number | undefined>;
  selectedAccount: Ref<BlockchainAccount<AddressData> | undefined>;
  selectedAsset: Ref<string | undefined>;
  selectedLocation: Ref<string>;
  selectedLocationLabel: Ref<string>;
  selectedProtocol: Ref<string | undefined>;
  source: Ref<HistoricalBalanceSource>;
  timestamp: Ref<number>;
}

export function useHistoricalBalances(): UseHistoricalBalancesReturn {
  const historicalBalancesStore = useHistoricalBalancesStore();
  const { savedFilters } = storeToRefs(historicalBalancesStore);
  const { setSavedFilters } = historicalBalancesStore;

  // Local filter state - initialized from saved filters if available
  const saved = get(savedFilters);
  const timestamp = ref<number>(saved?.timestamp ?? dayjs().unix());
  const selectedAsset = ref<string | undefined>(saved?.selectedAsset);
  const selectedLocation = ref<string>(saved?.selectedLocation ?? '');
  const selectedLocationLabel = ref<string>(saved?.selectedLocationLabel ?? '');
  const selectedProtocol = ref<string | undefined>(saved?.selectedProtocol);
  const source = ref<HistoricalBalanceSource>(saved?.source ?? Source.HISTORICAL_EVENTS);
  const selectedAccount = ref<BlockchainAccount<AddressData> | undefined>(saved?.selectedAccount);

  // Local results state
  const rawEntries = ref<Record<string, BigNumber>>({});
  const queriedTimestamp = ref<number>();
  const queryCompleted = ref<boolean>(false);

  const loading = ref<boolean>(false);
  const errorMessage = ref<string>();
  const fieldErrors = ref<ValidationErrors>({});

  // Flag to indicate if we have saved filters and should auto-fetch on mount
  const hasSavedFilters = computed<boolean>(() => !!get(savedFilters));

  const { t } = useI18n({ useScope: 'global' });

  const { fetchHistoricalBalances, fetchOnchainHistoricalBalance, processHistoricalBalances } = useHistoricalBalancesApi();
  const { getEvmChainName } = useSupportedChains();
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

    for (const [asset, amount] of Object.entries(entries)) {
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

    return HistoricalBalancesResponse.parse(result);
  }

  async function queryOnchainBalance(ts: number, chain: string, addr: string, asset: string): Promise<OnchainHistoricalBalanceResponse> {
    const evmChainName = getEvmChainName(chain);
    if (!evmChainName)
      throw new Error(t('historical_balances.errors.invalid_chain'));

    const payload = {
      address: addr,
      asset,
      evmChain: evmChainName,
      timestamp: ts,
    };

    const { taskId } = await fetchOnchainHistoricalBalance(payload);

    const { result } = await awaitTask<OnchainHistoricalBalanceResponse, TaskMeta>(
      taskId,
      TaskType.QUERY_ONCHAIN_HISTORICAL_BALANCE,
      {
        title: t('historical_balances.title'),
        description: t('historical_balances.onchain_task_description', {
          address: addr,
          asset,
          chain: evmChainName,
          timestamp: formatTimestamp(ts),
        }),
      },
    );

    return OnchainHistoricalBalanceResponse.parse(result);
  }

  async function fetchBalances(): Promise<void> {
    const ts = get(timestamp);
    const currentSource = get(source);

    set(loading, true);
    set(errorMessage, undefined);
    set(fieldErrors, {});
    set(rawEntries, {});
    set(queryCompleted, false);

    try {
      if (currentSource === Source.ARCHIVE_NODE) {
        const account = get(selectedAccount);
        const asset = get(selectedAsset);

        if (!account || !asset) {
          set(errorMessage, t('historical_balances.errors.missing_archive_node_fields'));
          set(loading, false);
          return;
        }

        const result = await queryOnchainBalance(ts, account.chain, account.data.address, asset);
        set(rawEntries, result ?? {});
      }
      else {
        const asset = get(selectedAsset);
        const location = get(selectedLocation) || undefined;
        const locationLabel = get(selectedLocationLabel) || undefined;
        const protocol = get(selectedProtocol);

        let result = await queryBalances(ts, asset, location, locationLabel, protocol);

        // Keep triggering processing until processing_required is false
        while (result.processingRequired) {
          await triggerProcessing();
          result = await queryBalances(ts, asset, location, locationLabel, protocol);
        }

        set(rawEntries, result.entries ?? {});
      }

      set(queriedTimestamp, ts);
      set(loading, false);
      set(queryCompleted, true);

      // Save filters to store only after successful fetch
      setSavedFilters({
        selectedAccount: get(selectedAccount),
        selectedAsset: get(selectedAsset),
        selectedLocation: get(selectedLocation),
        selectedLocationLabel: get(selectedLocationLabel),
        selectedProtocol: get(selectedProtocol),
        source: currentSource,
        timestamp: ts,
      });
    }
    catch (error: any) {
      if (error instanceof ApiValidationError) {
        const payload = { asset: get(selectedAsset) };
        const errors = error.getValidationErrors(payload);

        if (typeof errors === 'string') {
          set(errorMessage, errors);
        }
        else {
          set(fieldErrors, errors);
        }
      }
      else if (error.message?.includes('404') || error.message?.includes('No historical data')) {
        set(errorMessage, t('historical_balances.no_data'));
      }
      else {
        set(errorMessage, error.message);
      }

      set(loading, false);
    }
  }

  return {
    balances,
    errorMessage,
    fetchBalances,
    fieldErrors,
    hasResults,
    hasSavedFilters,
    loading,
    noDataFound,
    queriedTimestamp,
    selectedAccount,
    selectedAsset,
    selectedLocation,
    selectedLocationLabel,
    selectedProtocol,
    source,
    timestamp,
  };
}
