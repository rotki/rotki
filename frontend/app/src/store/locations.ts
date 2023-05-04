import { type Ref } from 'vue';
import { type ActionDataEntry } from '@/types/action';
import { type TradeLocationData } from '@/types/history/trade/location';

export const useLocationStore = defineStore('locations', () => {
  const tradeLocations: Ref<TradeLocationData[]> = ref([]);

  const { fetchAllLocations } = useHistoryApi();
  const { tc } = useI18n();

  const toTradeLocationData = (
    locations: Record<string, Omit<ActionDataEntry, 'identifier'>>
  ): TradeLocationData[] =>
    Object.entries(locations).map(([identifier, item]) => {
      const name = item.label
        ? item.label
        : tc(`backend_mappings.trade_location.${identifier}`)?.toString() ||
          toSentenceCase(identifier);

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
