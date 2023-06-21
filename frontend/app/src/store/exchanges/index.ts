import {
  type EditExchange,
  type Exchange,
  type ExchangeSetupPayload,
  type SupportedExchange
} from '@/types/exchanges';

export const useExchangesStore = defineStore('exchanges', () => {
  const exchangeBalancesStore = useExchangeBalancesStore();
  const { fetchExchangeBalances } = exchangeBalancesStore;
  const { exchangeBalances } = storeToRefs(exchangeBalancesStore);
  const sessionStore = useSessionSettingsStore();
  const { setConnectedExchanges } = sessionStore;
  const { connectedExchanges } = storeToRefs(sessionStore);

  const { queryRemoveExchange, querySetupExchange } = useExchangeApi();
  const { setMessage } = useMessageStore();

  const { t } = useI18n();

  const getExchangeNonce = (exchange: SupportedExchange): ComputedRef<number> =>
    computed(
      () =>
        get(connectedExchanges).filter(({ location }) => location === exchange)
          .length + 1
    );

  const addExchange = (exchange: Exchange): void => {
    setConnectedExchanges([...get(connectedExchanges), exchange]);
  };

  const editExchange = ({
    exchange: { location, name: oldName, krakenAccountType, ftxSubaccount },
    newName
  }: EditExchange): void => {
    const exchanges = [...get(connectedExchanges)];
    const name = newName ?? oldName;
    const index = exchanges.findIndex(
      value => value.name === oldName && value.location === location
    );
    exchanges[index] = {
      ...exchanges[index],
      name,
      location,
      krakenAccountType,
      ftxSubaccount
    };
    setConnectedExchanges(exchanges);
  };

  const removeExchange = async (exchange: Exchange): Promise<boolean> => {
    try {
      const success = await queryRemoveExchange(exchange);
      const connected = get(connectedExchanges);
      if (success) {
        const exchangeIndex = connected.findIndex(
          ({ location, name }) =>
            name === exchange.name && location === exchange.location
        );
        assert(
          exchangeIndex >= 0,
          `${exchange} not found in ${connected
            .map(exchange => `${exchange.name} on ${exchange.location}`)
            .join(', ')}`
        );

        const exchanges = [...connected];
        const balances = { ...get(exchangeBalances) };
        const index = exchanges.findIndex(
          ({ location, name }) =>
            name === exchange.name && location === exchange.location
        );
        // can't modify in place or else the vue reactivity does not work
        exchanges.splice(index, 1);
        delete balances[exchange.location];
        setConnectedExchanges(exchanges);
        set(exchangeBalances, balances);

        if (exchanges.length > 0) {
          await fetchExchangeBalances({
            location: exchange.location,
            ignoreCache: false
          });
        }
      }

      return success;
    } catch (e: any) {
      setMessage({
        title: t('actions.balances.exchange_removal.title'),
        description: t('actions.balances.exchange_removal.description', {
          exchange,
          error: e.message
        })
      });
      return false;
    }
  };

  const setupExchange = async ({
    exchange,
    edit
  }: ExchangeSetupPayload): Promise<boolean> => {
    try {
      const success = await querySetupExchange(exchange, edit);
      const exchangeEntry: Exchange = {
        name: exchange.name,
        location: exchange.location,
        krakenAccountType: exchange.krakenAccountType ?? undefined,
        ftxSubaccount: exchange.ftxSubaccount ?? undefined
      };

      if (!edit) {
        addExchange(exchangeEntry);
      } else {
        editExchange({
          exchange: exchangeEntry,
          newName: exchange.newName
        });
      }

      startPromise(
        fetchExchangeBalances({
          location: exchange.location,
          ignoreCache: false
        })
      );

      return success;
    } catch (e: any) {
      setMessage({
        title: t('actions.balances.exchange_setup.title').toString(),
        description: t('actions.balances.exchange_setup.description', {
          exchange: exchange.location,
          error: e.message
        }).toString()
      });
      return false;
    }
  };

  return {
    connectedExchanges,
    getExchangeNonce,
    addExchange,
    editExchange,
    removeExchange,
    setupExchange
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useExchangesStore, import.meta.hot));
}
