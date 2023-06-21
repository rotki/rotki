import { type ActionDataEntry } from '@/types/action';
import { type TradeLocationData } from '@/types/history/trade/location';

export const useLocationStore = defineStore('locations', () => {
  const tradeLocations: Ref<TradeLocationData[]> = ref([]);

  const { fetchAllLocations } = useHistoryApi();
  const { t, te } = useI18n();

  const toTradeLocationData = (
    locations: Record<string, Omit<ActionDataEntry, 'identifier'>>
  ): TradeLocationData[] =>
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

  const fetchAllTradeLocations = async () => {
    const { locations } = await fetchAllLocations();
    set(tradeLocations, toTradeLocationData(locations));
  };

  return {
    tradeLocations,
    fetchAllTradeLocations
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useLocationStore, import.meta.hot));
}
