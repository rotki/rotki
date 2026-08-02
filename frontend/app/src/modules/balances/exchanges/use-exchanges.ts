import type { ExchangeBalancePayload } from '@/modules/accounts/blockchain-accounts';
import { assert, toSentenceCase } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { map as mapResult, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { useValueThreshold } from '@/modules/assets/amount-display/use-usd-value-threshold';
import { useExchangeApi } from '@/modules/balances/api/use-exchange-api';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { AssetBalances } from '@/modules/balances/types/balances';
import { type EditExchange, Exchange, type ExchangeFormData } from '@/modules/balances/types/exchanges';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { EXCHANGE_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

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

  const { submitTask } = useNativeTask();
  const { notifyError, showErrorMessage } = useNotifications();
  const { exchangeBalances } = storeToRefs(useBalancesStore());
  const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
  const { setConnectedExchanges } = useConnectedExchangesStore();
  const { queryExchangeBalances } = useExchangeApi();
  const valueThreshold = useValueThreshold(BalanceSource.EXCHANGES);

  const { callSetupExchange, queryRemoveExchange } = useExchangeApi();

  const fetchExchangeBalances = async (payload: ExchangeBalancePayload): Promise<void> => {
    const { ignoreCache, location } = payload;
    const threshold = get(valueThreshold);

    // One native activity per exchange location; liveness/freshness are read off the orchestrator
    // (`useWorkStatus(ActivityKind.EXCHANGE_BALANCES)` globally, or with `location` per-exchange).
    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.EXCHANGE_BALANCES, location),
      kind: ActivityKind.EXCHANGE_BALANCES,
      lane: EXCHANGE_LANE,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<AssetBalances>(
          async () => queryExchangeBalances(location, ignoreCache, threshold),
        ),
        (result) => {
          set(exchangeBalances, {
            ...get(exchangeBalances),
            [location]: AssetBalances.parse(result),
          });
        },
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.exchange_balances.query'), { location: toSentenceCase(location) }),
      title: t('task_center.group.exchange_balances'),
    });

    onActionableError(outcome, (error) => {
      notifyError(
        t('actions.balances.exchange_balances.error.title', { location: toSentenceCase(location) }),
        t('actions.balances.exchange_balances.error.message', { error: error.message, location }),
      );
    });
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

  const editExchange = ({ exchange: { gateLocation, krakenAccountType, location, name: oldName, okxLocation }, newName }: EditExchange): void => {
    const exchanges = [...get(connectedExchanges)];
    const name = newName ?? oldName;
    const index = exchanges.findIndex(value => value.name === oldName && value.location === location);
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
      if (isRequestCancellation(error))
        return false;

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
    const { gateLocation, krakenAccountType, krakenFuturesApiKey, krakenFuturesApiSecret, location, mode, newName, okxLocation } = exchange;

    const filteredPayload: ExchangeFormData = {
      ...exchange,
      krakenAccountType: location === 'kraken' ? krakenAccountType : undefined,
      krakenFuturesApiKey: location === 'kraken' ? krakenFuturesApiKey : undefined,
      krakenFuturesApiSecret: location === 'kraken' ? krakenFuturesApiSecret : undefined,
      gateLocation: location === 'gate' ? gateLocation : undefined,
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
