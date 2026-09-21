import type { ExchangeConnector } from '@/modules/balances/types/exchanges';
import type { AllLocation, TradeLocationData } from '@/modules/core/common/location';
import { toSentenceCase } from '@rotki/common';
import { getPublicProtocolImagePath } from '@/modules/core/common/file/file';

export const useLocationStore = defineStore('locations', () => {
  const allLocations = ref<AllLocation>({});
  /** The supported exchange connectors and what their setup needs. */
  const exchangeConnectors = ref<ExchangeConnector[]>([]);

  // eslint-disable-next-line @typescript-eslint/unbound-method -- vue-i18n binds t and te to the composer it returns, so destructuring them is safe
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
    return Object.keys(locations).filter(key => locations[key].isExchange === true);
  });

  /** The exchange connectors an API key can be set up for. */
  const exchangesWithKey = computed<string[]>(() => get(exchangeConnectors).map(item => item.connector));

  const exchangesWithPassphrase = computed<string[]>(() =>
    get(exchangeConnectors).filter(item => item.isExchangeWithPassphrase).map(item => item.connector));

  const exchangesWithoutApiSecret = computed<string[]>(() =>
    get(exchangeConnectors).filter(item => item.isExchangeWithoutApiSecret).map(item => item.connector));

  const experimentalExchanges = computed<string[]>(() =>
    get(exchangeConnectors).filter(item => item.experimental).map(item => item.connector));

  function useIsExperimentalExchange(location: MaybeRefOrGetter<string>): ComputedRef<boolean> {
    return computed(() => get(experimentalExchanges).includes(toValue(location)));
  }

  return {
    allExchanges,
    allLocations,
    exchangeConnectors,
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
