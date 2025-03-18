import type { ExchangeBalancePayload } from '@/types/blockchain/accounts';
import type { EditExchange, Exchange, ExchangeFormData } from '@/types/exchanges';
import type { ExchangeMeta } from '@/types/task';
import { useExchangeApi } from '@/composables/api/balances/exchanges';
import { useStatusUpdater } from '@/composables/status';
import { useUsdValueThreshold } from '@/composables/usd-value-threshold';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useMessageStore } from '@/store/message';
import { useNotificationsStore } from '@/store/notifications';
import { useSessionSettingsStore } from '@/store/settings/session';
import { useTaskStore } from '@/store/tasks';
import { AssetBalances } from '@/types/balances';
import { BalanceSource } from '@/types/settings/frontend-settings';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { assert, toSentenceCase } from '@rotki/common';
import { startPromise } from '@shared/utils';

interface UseExchangesReturn {
  fetchConnectedExchangeBalances: (refresh?: boolean) => Promise<void>;
  fetchExchangeBalances: (payload: ExchangeBalancePayload) => Promise<void>;
  addExchange: (exchange: Exchange) => void;
  editExchange: (payload: EditExchange) => void;
  removeExchange: (exchange: Exchange) => Promise<boolean>;
  setupExchange: (exchange: ExchangeFormData) => Promise<boolean>;
}

export function useExchanges(): UseExchangesReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { awaitTask, isTaskRunning, metadata } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { exchangeBalances } = storeToRefs(useBalancesStore());
  const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
  const { setConnectedExchanges } = useSessionSettingsStore();
  const { queryExchangeBalances } = useExchangeApi();
  const balanceUsdValueThreshold = useUsdValueThreshold(BalanceSource.EXCHANGES);

  const { callSetupExchange, queryRemoveExchange } = useExchangeApi();
  const { setMessage } = useMessageStore();

  const fetchExchangeBalances = async (payload: ExchangeBalancePayload): Promise<void> => {
    const { ignoreCache, location } = payload;
    const taskType = TaskType.QUERY_EXCHANGE_BALANCES;
    const meta = metadata<ExchangeMeta>(taskType);

    const threshold = get(balanceUsdValueThreshold);

    if (isTaskRunning(taskType) && meta?.location === location)
      return;

    const { isFirstLoad, resetStatus, setStatus } = useStatusUpdater(Section.EXCHANGES);

    const newStatus = isFirstLoad() ? Status.LOADING : Status.REFRESHING;
    setStatus(newStatus);

    try {
      const { taskId } = await queryExchangeBalances(location, ignoreCache, threshold);
      const meta: ExchangeMeta = {
        location,
        title: t('actions.balances.exchange_balances.task.title', {
          location,
        }),
      };

      const { result } = await awaitTask<AssetBalances, ExchangeMeta>(taskId, taskType, meta, true);

      set(exchangeBalances, {
        ...get(exchangeBalances),
        [location]: AssetBalances.parse(result),
      });
      setStatus(Status.LOADED);
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        const message = t('actions.balances.exchange_balances.error.message', {
          error: error.message,
          location,
        });
        const title = t('actions.balances.exchange_balances.error.title', {
          location: toSentenceCase(location),
        });

        notify({
          display: true,
          message,
          title,
        });
      }
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
    editExchange,
    fetchConnectedExchangeBalances,
    fetchExchangeBalances,
    removeExchange,
    setupExchange,
  };
}
