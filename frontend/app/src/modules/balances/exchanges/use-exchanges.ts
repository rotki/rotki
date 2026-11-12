import type { ExchangeBalancePayload } from '@/modules/accounts/blockchain-accounts';
import { assert, toSentenceCase } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { err, flatMap as flatMapResult, ok, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { useValueThreshold } from '@/modules/assets/amount-display/use-usd-value-threshold';
import { useExchangeApi } from '@/modules/balances/api/use-exchange-api';
import { exchangeBalancesActivity } from '@/modules/balances/balances.activity';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { ExchangeBalancesResponse } from '@/modules/balances/types/balances';
import { type EditExchange, Exchange, type ExchangeData, type ExchangeFormData } from '@/modules/balances/types/exchanges';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { FailureCause, isRetryableCause, parseFailureCause } from '@/modules/core/api/failure-cause';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { balanceSum } from '@/modules/core/common/data/calculation';
import { type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';

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

/**
 * The cause a location's failed connections report together.
 *
 * @remarks
 * A rerun queries every connection of the location, so a retry is worth offering as soon as one of
 * them could heal, even beside one that needs a new key.
 */
function locationFailureCause(causes: string[]): FailureCause {
  const parsed = causes.map(parseFailureCause);
  return parsed.find(isRetryableCause) ?? parsed[0] ?? FailureCause.UNKNOWN;
}

export function useExchanges(): UseExchangesReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { submitTask } = useNativeTask();
  const { exchangeAccountBalances, exchangeBalances } = storeToRefs(useBalancesStore());
  const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
  const { setConnectedExchanges } = useConnectedExchangesStore();
  const { queryExchangeBalances } = useExchangeApi();
  const valueThreshold = useValueThreshold(BalanceSource.EXCHANGES);

  const { callSetupExchange, queryRemoveExchange } = useExchangeApi();

  /**
   * Refreshes one exchange's balances.
   *
   * @remarks
   * One native activity per location, {@link exchangeBalancesActivity}, so liveness and freshness
   * are read off the orchestrator: by its kind for all of them, or by its parts for one.
   *
   * A connection that failed is missing from the location's totals, which would then understate
   * the holdings. Successful accounts update, but failed accounts and location totals stay in place.
   */
  const fetchExchangeBalances = async (payload: ExchangeBalancePayload): Promise<void> => {
    const { ignoreCache, location } = payload;
    const threshold = get(valueThreshold);

    await submitTask({
      id: exchangeBalancesActivity.id({ location }),
      kind: exchangeBalancesActivity.kind,
      lane: exchangeBalancesActivity.laneOf?.({ location }),
      rerunnable: true,
      run: async ({ rerun, runTask }): Promise<Result<void, TaskError>> => flatMapResult(
        await runTask<ExchangeBalancesResponse>(
          async () => queryExchangeBalances(location, rerun || ignoreCache === true, threshold),
        ),
        (result): Result<void, TaskError> => {
          const { failedAccounts, perAccount, totals } = ExchangeBalancesResponse.parse(result);
          const failedConnections = Object.entries(failedAccounts?.[location] ?? {});
          const failures = failedConnections.map(([identifier, { message }]) => {
            const connection = get(connectedExchanges).find(exchange => exchange.identifier === identifier);
            return `${connection?.name ?? identifier}: ${message}`;
          });
          set(exchangeAccountBalances, {
            ...get(exchangeAccountBalances),
            [location]: failures.length > 0
              ? { ...get(exchangeAccountBalances)[location], ...perAccount[location] }
              : perAccount[location] ?? {},
          });
          if (failures.length > 0) {
            return err(TaskFailed({
              failureCause: locationFailureCause(failedConnections.map(([, { cause }]) => cause)),
              message: failures.join(' '),
            }));
          }

          set(exchangeBalances, {
            ...get(exchangeBalances),
            [location]: totals[location] ?? {},
          });
          return ok(undefined);
        },
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.exchange_balances.query'), { location: toSentenceCase(location) }),
      title: t('task_center.group.exchange_balances'),
    });
  };

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
