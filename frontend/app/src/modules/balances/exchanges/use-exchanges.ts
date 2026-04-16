import type { ExchangeBalancePayload } from '@/modules/accounts/blockchain-accounts';
import type { ExchangeMeta } from '@/modules/tasks/types';
import { assert, toSentenceCase } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useExchangeApi } from '@/composables/api/balances/exchanges';
import { useStatusUpdater } from '@/composables/status';
import { useValueThreshold } from '@/composables/usd-value-threshold';
import { AssetBalances } from '@/modules/balances/types/balances';
import { type EditExchange, Exchange, type ExchangeFormData } from '@/modules/balances/types/exchanges';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { getErrorMessage } from '@/modules/common/logging/error-handling';
import { Section, Status } from '@/modules/common/status';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';
import { TaskType } from '@/modules/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/tasks/use-task-handler';
import { useSessionSettingsStore } from '@/store/settings/session';

interface UseExchangesReturn {
  fetchConnectedExchangeBalances: (refresh?: boolean) => Promise<void>;
  fetchSelectedExchangeBalances: (exchangeLocation: string) => Promise<void>;
  fetchExchangeBalances: (payload: ExchangeBalancePayload) => Promise<void>;
  addExchange: (exchange: Exchange) => void;
  editExchange: (payload: EditExchange) => void;
  removeExchange: (exchange: Exchange) => Promise<boolean>;
  setupExchange: (exchange: ExchangeFormData) => Promise<boolean>;
}

export function useExchanges(): UseExchangesReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { runTask } = useTaskHandler();
  const { notifyError, showErrorMessage } = useNotifications();
  const { exchangeBalances } = storeToRefs(useBalancesStore());
  const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
  const { setConnectedExchanges } = useSessionSettingsStore();
  const { queryExchangeBalances } = useExchangeApi();
  const valueThreshold = useValueThreshold(BalanceSource.EXCHANGES);

  const { callSetupExchange, queryRemoveExchange } = useExchangeApi();

  const fetchExchangeBalances = async (payload: ExchangeBalancePayload): Promise<void> => {
    const { ignoreCache, location } = payload;
    const threshold = get(valueThreshold);

    const { isFirstLoad, resetStatus, setStatus } = useStatusUpdater(Section.EXCHANGES);

    const newStatus = isFirstLoad() ? Status.LOADING : Status.REFRESHING;
    setStatus(newStatus);

    const outcome = await runTask<AssetBalances, ExchangeMeta>(
      async () => queryExchangeBalances(location, ignoreCache, threshold),
      { type: TaskType.QUERY_EXCHANGE_BALANCES, meta: {
        location,
        title: t('actions.balances.exchange_balances.task.title', { location }),
      }, unique: false },
    );

    if (outcome.success) {
      set(exchangeBalances, {
        ...get(exchangeBalances),
        [location]: AssetBalances.parse(outcome.result),
      });
      setStatus(Status.LOADED);
    }
    else if (isActionableFailure(outcome)) {
      const message = t('actions.balances.exchange_balances.error.message', {
        error: outcome.message,
        location,
      });
      const title = t('actions.balances.exchange_balances.error.title', {
        location: toSentenceCase(location),
      });

      notifyError(title, message);
      resetStatus();
    }
  };

  const fetchConnectedExchangeBalances = async (refresh = false): Promise<void> => {
    const exchanges = get(connectedExchanges);
    for (const exchange of exchanges) {
      await fetchExchangeBalances({
        ignoreCache: refresh,
        location: exchange.location,
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

  const editExchange = ({ exchange: { krakenAccountType, location, name: oldName, okxLocation }, newName }: EditExchange): void => {
    const exchanges = [...get(connectedExchanges)];
    const name = newName ?? oldName;
    const index = exchanges.findIndex(value => value.name === oldName && value.location === location);
    exchanges[index] = {
      ...exchanges[index],
      krakenAccountType,
      location,
      name,
      okxLocation,
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
            location: exchange.location,
          });
        }
      }

      return success;
    }
    catch (error: unknown) {
      showErrorMessage(
        t('actions.balances.exchange_removal.title'),
        t('actions.balances.exchange_removal.description', {
          error: getErrorMessage(error),
          exchange,
        }),
      );
      return false;
    }
  };

  const setupExchange = async (exchange: ExchangeFormData): Promise<boolean> => {
    const { krakenAccountType, krakenFuturesApiKey, krakenFuturesApiSecret, location, mode, newName, okxLocation } = exchange;

    const filteredPayload: ExchangeFormData = {
      ...exchange,
      krakenAccountType: location === 'kraken' ? krakenAccountType : undefined,
      krakenFuturesApiKey: location === 'kraken' ? krakenFuturesApiKey : undefined,
      krakenFuturesApiSecret: location === 'kraken' ? krakenFuturesApiSecret : undefined,
      okxLocation: location === 'okx' ? okxLocation : undefined,
    };

    const success = await callSetupExchange(filteredPayload);

    // Only get the essential exchange data to store in memory, excluding the api key and secret
    const essentialExchangeData = Exchange.parse(filteredPayload);

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

    return success;
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
