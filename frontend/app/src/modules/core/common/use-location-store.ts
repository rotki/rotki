import type { AllLocation, TradeLocationData } from '@/modules/core/common/location';
import { toSentenceCase } from '@rotki/common';
import { getPublicProtocolImagePath } from '@/modules/core/common/file/file';

export const useLocationStore = defineStore('locations', () => {
  const allLocations = ref<AllLocation>({});

  // eslint-disable-next-line @typescript-eslint/unbound-method
  const { t, te } = useI18n({ useScope: 'global' });

  const toTradeLocationData = (locations: AllLocation): TradeLocationData[] =>
    Object.entries(locations).map(([identifier, item]) => {
      let name: string;

      if (item.label) {
        name = item.label;
      }
      else {
        const translationKey = `backend_mappings.trade_location.${identifier}`;
        if (te(translationKey))
          name = t(translationKey);
        else name = toSentenceCase(identifier);
      }

      const mapped = {
        identifier,
        ...item,
        name,
      };

      if (item.image)
        mapped.image = getPublicProtocolImagePath(item.image);

      return mapped;
    });

  const tradeLocations = computed(() => toTradeLocationData(get(allLocations)));

  const allExchanges = computed<string[]>(() => {
    const locations = get(allLocations);
    return Object.keys(locations).filter((key) => {
      const location = locations[key];
      return location.isExchange || location.exchangeDetails;
    });
  });

  const exchangesWithKey = computed<string[]>(() => {
    const locations = get(allLocations);
    return get(allExchanges).filter(key => locations[key].exchangeDetails?.isExchangeWithKey);
  });

  const exchangesWithPassphrase = computed<string[]>(() => {
    const locations = get(allLocations);
    return get(exchangesWithKey).filter(key => locations[key].exchangeDetails?.isExchangeWithPassphrase);
  });

  const exchangesWithoutApiSecret = computed<string[]>(() => {
    const locations = get(allLocations);
    return get(exchangesWithKey).filter(key => locations[key].exchangeDetails?.isExchangeWithoutApiSecret);
  });

  const experimentalExchanges = computed<string[]>(() => {
    const locations = get(allLocations);
    return get(exchangesWithKey).filter(key => locations[key].exchangeDetails?.experimental);
  });

  function useIsExperimentalExchange(location: MaybeRefOrGetter<string>): ComputedRef<boolean> {
    return computed(() => get(experimentalExchanges).includes(toValue(location)));
  }

  return {
    allExchanges,
    allLocations,
    exchangesWithKey,
    exchangesWithoutApiSecret,
    exchangesWithPassphrase,
    experimentalExchanges,
    tradeLocations,
    useIsExperimentalExchange,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useLocationStore, import.meta.hot));
