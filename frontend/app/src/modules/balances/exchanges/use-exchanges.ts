import type { ExchangeBalancePayload } from '@/modules/accounts/blockchain-accounts';
import { assert } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { get, set } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { useValueThreshold } from '@/modules/assets/amount-display/use-usd-value-threshold';
import { useExchangeApi } from '@/modules/balances/api/use-exchange-api';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useExchangeBalancesQuery } from '@/modules/balances/exchanges/use-exchange-balances-query';
import { type EditExchange, Exchange, type ExchangeData, type ExchangeFormData } from '@/modules/balances/types/exchanges';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { balanceSum } from '@/modules/core/common/data/calculation';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';

interface UseExchangesReturn {
  fetchConnectedExchangeBalances: (refresh?: boolean) => Promise<void>;
  fetchSelectedExchangeBalances: (exchangeLocation: string) => Promise<void>;
  fetchExchangeBalances: (payload: ExchangeBalancePayload) => Promise<void>;
  addExchange: (exchange: Exchange) => void;
  editExchange: (payload: EditExchange) => void;
  /**
   * Disconnects an exchange and drops it and its balances from the store.
   *
   * @remarks
   * Resolves `false` when the backend refused or the request was cancelled. Any other failure
   * rejects, for the caller to name beside the row it came from.
   */
  removeExchange: (exchange: Exchange) => Promise<boolean>;
  setupExchange: (exchange: ExchangeFormData) => Promise<void>;
}

export function useExchanges(): UseExchangesReturn {
  const { exchangeAccountBalances, exchangeBalances } = storeToRefs(useBalancesStore());
  const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
  const { setConnectedExchanges } = useConnectedExchangesStore();
  const { callSetupExchange, queryRemoveExchange } = useExchangeApi();
  const valueThreshold = useValueThreshold(BalanceSource.EXCHANGES);
  const { fetchExchangeBalances } = useExchangeBalancesQuery();

  /**
   * Refreshes every exchange with a connection, once per exchange.
   *
   * @remarks
   * One query of a location returns all of its connections, so querying it once per connection
   * repeats the same work as many times as the exchange has accounts.
   */
  const fetchConnectedExchangeBalances = async (refresh = false): Promise<void> => {
    const locations = new Set(get(connectedExchanges).map(({ location }) => location));
    for (const location of locations) {
      await fetchExchangeBalances({
        ignoreCache: refresh,
        location,
      });
    }
  };

  const fetchSelectedExchangeBalances = async (exchangeLocation: string): Promise<void> => {
    await fetchExchangeBalances({
      ignoreCache: true,
      location: exchangeLocation,
    });
  };
  const addExchange = (exchange: Exchange): void => {
    setConnectedExchanges([...get(connectedExchanges), exchange]);
  };

  const editExchange = ({ exchange: { gateLocation, identifier, krakenAccountType, location, name: oldName, okxLocation }, newName }: EditExchange): void => {
    const exchanges = [...get(connectedExchanges)];
    const name = newName ?? oldName;
    const index = exchanges.findIndex(value => value.identifier === identifier);
    exchanges[index] = {
      ...exchanges[index],
      gateLocation,
      krakenAccountType,
      location,
      name,
      okxLocation,
    };
    setConnectedExchanges(exchanges);
  };

  function totalsForAccounts(accounts: ExchangeData): ExchangeData[string] {
    const totals: ExchangeData[string] = {};
    for (const assets of Object.values(accounts)) {
      for (const [asset, balance] of Object.entries(assets))
        totals[asset] = totals[asset] ? balanceSum(totals[asset], balance) : balance;
    }
    const threshold = get(valueThreshold);
    return Object.fromEntries(
      Object.entries(totals).filter(([, balance]) => threshold === undefined || balance.value.gt(threshold)),
    );
  }

  const removeExchange = async (exchange: Exchange): Promise<boolean> => {
    try {
      const success = await queryRemoveExchange(exchange);
      const connected = get(connectedExchanges);
      if (success) {
        const exchangeIndex = connected.findIndex(
          ({ identifier }) => identifier === exchange.identifier,
        );
        assert(
          exchangeIndex >= 0,
          `${exchange.location} not found in ${connected
            .map(exchange => `${exchange.name} on ${exchange.location}`)
            .join(', ')}`,
        );

        const exchanges = [...connected];
        const balances = { ...get(exchangeBalances) };
        const accountBalances = { ...get(exchangeAccountBalances) };
        const locationAccounts = { ...accountBalances[exchange.location] };
        delete locationAccounts[exchange.identifier];
        if (Object.keys(locationAccounts).length > 0)
          accountBalances[exchange.location] = locationAccounts;
        else
          delete accountBalances[exchange.location];
        exchanges.splice(exchangeIndex, 1);
        if (Object.keys(locationAccounts).length > 0) {
          balances[exchange.location] = totalsForAccounts(locationAccounts);
        }
        else {
          delete balances[exchange.location];
        }
        setConnectedExchanges(exchanges);
        set(exchangeBalances, balances);
        set(exchangeAccountBalances, accountBalances);

        if (exchanges.some(exch => exch.location === exchange.location)) {
          await fetchExchangeBalances({
            location: exchange.location,
          });
        }
      }

      return success;
    }
    catch (error: unknown) {
      if (isRequestCancellation(error))
        return false;

      throw error;
    }
  };

  const setupExchange = async (exchange: ExchangeFormData): Promise<void> => {
    const { binanceHistoryStartTs, gateLocation, krakenAccountType, krakenFuturesApiKey, krakenFuturesApiSecret, location, mode, newName, okxLocation } = exchange;

    const filteredPayload: ExchangeFormData = {
      ...exchange,
      krakenAccountType: location === 'kraken' ? krakenAccountType : undefined,
      krakenFuturesApiKey: location === 'kraken' ? krakenFuturesApiKey : undefined,
      krakenFuturesApiSecret: location === 'kraken' ? krakenFuturesApiSecret : undefined,
      binanceHistoryStartTs: ['binance', 'binanceus'].includes(location) && mode === 'add'
        ? binanceHistoryStartTs
        : undefined,
      gateLocation: location === 'gate' ? gateLocation : undefined,
      okxLocation: location === 'okx' ? okxLocation : undefined,
    };

    const identifier = await callSetupExchange(filteredPayload);

    // Only get the essential exchange data to store in memory, excluding the api key and secret
    const essentialExchangeData = Exchange.parse({ ...filteredPayload, connector: location, identifier });

    if (mode !== 'edit') {
      addExchange(essentialExchangeData);
    }
    else {
      editExchange({
        exchange: essentialExchangeData,
        newName,
      });
    }

    startPromise(
      fetchExchangeBalances({
        location,
      }),
    );
  };

  return {
    addExchange,
    editExchange,
    fetchConnectedExchangeBalances,
    fetchExchangeBalances,
    fetchSelectedExchangeBalances,
    removeExchange,
    setupExchange,
  };
}
