import { type TradeLocationData } from '@/types/history/trade/location';
import { type AllLocation } from '@/types/location';

export const useLocationStore = defineStore('locations', () => {
  const allLocations: Ref<AllLocation> = ref({});

  const { fetchAllLocations } = useHistoryApi();
  const { t, te } = useI18n();

  const toTradeLocationData = (locations: AllLocation): TradeLocationData[] =>
    Object.entries(locations).map(([identifier, item]) => {
      let name: string;

      if (item.label) {
        name = item.label;
      } else {
        const translationKey = `backend_mappings.trade_location.${identifier}`;
        if (te(translationKey)) {
          name = t(translationKey);
        } else {
          name = toSentenceCase(identifier);
        }
      }

      const mapped = {
        identifier,
        ...item,
        name
      };

      if (item.image) {
        mapped.image = `./assets/images/protocols/${item.image}`;
      }

      return mapped;
    });

  const tradeLocations = computed(() => toTradeLocationData(get(allLocations)));

  const fetchAllTradeLocations = async () => {
    const { locations } = await fetchAllLocations();
    set(allLocations, locations);
  };

  const allExchanges: ComputedRef<string[]> = computed(() => {
    const locations = get(allLocations);
    return Object.keys(locations).filter(key => {
      const location = locations[key];
      return location.isExchange || location.exchangeDetails;
    });
  });

  const exchangesWithKey: ComputedRef<string[]> = computed(() => {
    const locations = get(allLocations);
    return get(allExchanges).filter(
      key => locations[key].exchangeDetails?.isExchangeWithKey
    );
  });

  const exchangesWithPassphrase: ComputedRef<string[]> = computed(() => {
    const locations = get(allLocations);
    return get(exchangesWithKey).filter(
      key => locations[key].exchangeDetails?.isExchangeWithPassphrase
    );
  });

  const exchangesWithoutApiSecret: ComputedRef<string[]> = computed(() => {
    const locations = get(allLocations);
    return get(exchangesWithKey).filter(
      key => locations[key].exchangeDetails?.isExchangeWithoutApiSecret
    );
  });

  return {
    tradeLocations,
    fetchAllTradeLocations,
    allExchanges,
    exchangesWithKey,
    exchangesWithPassphrase,
    exchangesWithoutApiSecret
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useLocationStore, import.meta.hot));
}
