import type {
  KrakenStakingDateFilter,
  KrakenStakingEvents,
  KrakenStakingPagination,
} from '@/modules/staking/staking-types';
import { type AssetBalance, Zero } from '@rotki/common';
import { omit } from 'es-toolkit';
import { useResolveAssetIdentifier } from '@/modules/assets/use-resolve-asset-identifier';
import { balanceSum } from '@/modules/core/common/data/calculation';

function defaultPagination(): KrakenStakingPagination {
  return {
    ascending: [false],
    limit: 10,
    offset: 0,
    orderByAttributes: ['timestamp'],
  };
}

function defaultEventState(): KrakenStakingEvents {
  return {
    assets: [],
    entriesFound: 0,
    entriesLimit: 0,
    entriesTotal: 0,
    received: [],
    totalValue: Zero,
  };
}

export const useKrakenStakingStore = defineStore('staking/kraken', () => {
  const pagination = ref<KrakenStakingPagination>(defaultPagination());
  const rawEvents = ref<KrakenStakingEvents>(defaultEventState());
  /**
   * The page spinner, held here rather than derived from a work status: it spans an orchestrator
   * refresh *and* a plain task-less events read, so no single status covers it.
   */
  const loading = shallowRef<boolean>(false);
  const loadedOnce = shallowRef<boolean>(false);

  const isInitialLoading = computed<boolean>(() => get(loading) && !get(loadedOnce));

  /**
   * The date bounds of the query, as the filter bar reads and writes them.
   *
   * @remarks
   * A view onto `pagination`, not state of its own. Every read sends the whole object, so bounds
   * held anywhere else can be read from a snapshot taken before the user changed them.
   */
  const dateFilter = computed<KrakenStakingDateFilter>({
    get() {
      const { fromTimestamp, toTimestamp } = get(pagination);
      return { fromTimestamp, toTimestamp };
    },
    set({ fromTimestamp, toTimestamp }) {
      set(pagination, {
        ...omit(get(pagination), ['fromTimestamp', 'toTimestamp']),
        ...(fromTimestamp === undefined ? {} : { fromTimestamp }),
        ...(toTimestamp === undefined ? {} : { toTimestamp }),
      });
    },
  });

  /**
   * A value-stable key for those bounds. Watching `dateFilter` itself would fire on every
   * `pagination` write, including a page-size change, and re-query for a filter that did not move.
   */
  const dateFilterKey = computed<string>(() => {
    const { fromTimestamp, toTimestamp } = get(dateFilter);
    return `${fromTimestamp ?? ''}:${toTimestamp ?? ''}`;
  });

  const resolveAssetIdentifier = useResolveAssetIdentifier();

  const events = computed<KrakenStakingEvents>(() => {
    const eventsValue = get(rawEvents);
    const received = eventsValue.received;

    const receivedAssets: Record<string, AssetBalance> = {};

    for (const item of received) {
      const associatedAsset: string = resolveAssetIdentifier(item.asset);
      const existing = receivedAssets[associatedAsset];

      receivedAssets[associatedAsset] = existing
        ? { ...item, ...balanceSum(existing, item) }
        : { ...item };
    }

    return {
      ...eventsValue,
      assets: Object.keys(receivedAssets),
      received: Object.values(receivedAssets),
    };
  });

  return {
    dateFilter,
    dateFilterKey,
    events,
    isInitialLoading,
    loadedOnce,
    loading,
    pagination,
    rawEvents,
  };
});
