import type { EditExchange, Exchange, ExchangeFormData } from '@/types/exchanges';
import { useExchangeApi } from '@/composables/api/balances/exchanges';
import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import { useMessageStore } from '@/store/message';
import { useSessionSettingsStore } from '@/store/settings/session';
import { assert } from '@rotki/common';
import { startPromise } from '@shared/utils';

export const useExchangesStore = defineStore('exchanges', () => {
  const exchangeBalancesStore = useExchangeBalancesStore();
  const { fetchExchangeBalances } = exchangeBalancesStore;
  const { exchangeBalances } = storeToRefs(exchangeBalancesStore);
  const sessionStore = useSessionSettingsStore();
  const { setConnectedExchanges } = sessionStore;
  const { connectedExchanges } = storeToRefs(sessionStore);

  const { callSetupExchange, queryRemoveExchange } = useExchangeApi();
  const { setMessage } = useMessageStore();

  const { t } = useI18n();

  const getExchangeNonce = (exchange: string): ComputedRef<number> =>
    computed(() => get(connectedExchanges).filter(({ location }) => location === exchange).length + 1);

  const addExchange = (exchange: Exchange): void => {
    setConnectedExchanges([...get(connectedExchanges), exchange]);
  };

  const editExchange = ({ exchange: { krakenAccountType, location, name: oldName }, newName }: EditExchange): void => {
    const exchanges = [...get(connectedExchanges)];
    const name = newName ?? oldName;
    const index = exchanges.findIndex(value => value.name === oldName && value.location === location);
    exchanges[index] = {
      ...exchanges[index],
      krakenAccountType,
      location,
      name,
    };
    setConnectedExchanges(exchanges);
  };

  const removeExchange = async (exchange: Exchange): Promise<boolean> => {
    try {
      const success = await queryRemoveExchange(exchange);
      const connected = get(connectedExchanges);
      if (success) {
        const exchangeIndex = connected.findIndex(
          ({ location, name }) => name === exchange.name && location === exchange.location,
        );
        assert(
          exchangeIndex >= 0,
          `${exchange.location} not found in ${connected
            .map(exchange => `${exchange.name} on ${exchange.location}`)
            .join(', ')}`,
        );

        const exchanges = [...connected];
        const balances = { ...get(exchangeBalances) };
        const index = exchanges.findIndex(
          ({ location, name }) => name === exchange.name && location === exchange.location,
        );
        // can't modify in place or else the vue reactivity does not work
        exchanges.splice(index, 1);
        delete balances[exchange.location];
        setConnectedExchanges(exchanges);
        set(exchangeBalances, balances);

        // if multiple keys exist for the deleted exchange, re-fetch and update the balances for the location
        if (exchanges.some(exch => exch.location === exchange.location)) {
          await fetchExchangeBalances({
            ignoreCache: false,
            location: exchange.location,
          });
        }
      }

      return success;
    }
    catch (error: any) {
      setMessage({
        description: t('actions.balances.exchange_removal.description', {
          error: error.message,
          exchange,
        }),
        title: t('actions.balances.exchange_removal.title'),
      });
      return false;
    }
  };

  const setupExchange = async (exchange: ExchangeFormData): Promise<boolean> => {
    try {
      const success = await callSetupExchange(exchange);
      const { krakenAccountType, location, mode, name, newName } = exchange;
      const exchangeEntry: Exchange = {
        krakenAccountType,
        location,
        name,
      };

      if (mode !== 'edit') {
        addExchange(exchangeEntry);
      }
      else {
        editExchange({
          exchange: exchangeEntry,
          newName,
        });
      }

      startPromise(
        fetchExchangeBalances({
          ignoreCache: false,
          location,
        }),
      );

      return success;
    }
    catch (error: any) {
      setMessage({
        description: t('actions.balances.exchange_setup.description', {
          error: error.message,
          exchange: exchange.location,
        }),
        title: t('actions.balances.exchange_setup.title'),
      });
      return false;
    }
  };

  return {
    addExchange,
    connectedExchanges,
    editExchange,
    getExchangeNonce,
    removeExchange,
    setupExchange,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useExchangesStore, import.meta.hot));
