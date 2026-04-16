import type {
  KrakenStakingEvents,
  KrakenStakingPagination,
} from '@/modules/staking/staking-types';
import { type AssetBalance, Zero } from '@rotki/common';
import { useResolveAssetIdentifier } from '@/composables/assets/common';
import { balanceSum } from '@/modules/common/data/calculation';

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
    events,
    pagination,
    rawEvents,
  };
});
