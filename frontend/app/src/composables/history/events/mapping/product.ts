import type { HistoryEventProductData } from '@/types/history/events/event-type';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useRefMap } from '@/composables/utils/useRefMap';

export const useHistoryEventProductMappings = createSharedComposable(() => {
  const { getHistoryEventProductsData } = useHistoryEventsApi();

  const defaultHistoryEventProductsData = (): HistoryEventProductData => ({
    mappings: {},
    products: [],
  });

  const historyEventProductsData: Ref<HistoryEventProductData> = asyncComputed<HistoryEventProductData>(
    async () => getHistoryEventProductsData(),
    defaultHistoryEventProductsData(),
  );

  const historyEventProductsMapping = useRefMap(historyEventProductsData, ({ mappings }) => mappings);

  const historyEventProducts = useRefMap(historyEventProductsData, ({ products }) => products);

  return {
    historyEventProducts,
    historyEventProductsData,
    historyEventProductsMapping,
  };
});
