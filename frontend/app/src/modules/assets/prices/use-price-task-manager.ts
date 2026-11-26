import type { BigNumber } from '@rotki/common';
import type { FetchPricePayload } from '@/modules/accounts/blockchain-accounts';
import type { SupportedCurrency } from '@/modules/assets/amount-display/currencies';
import type { HistoricPricePayload, OracleCachePayload } from '@/modules/assets/prices/price-types';
import { get, set } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { err, flatMap, isErr, ok, type Result } from 'plainfp/result';
import { useI18n } from 'vue-i18n';
import { msg } from '@/message-key';
import { exchangeRatesActivity, latestPricesRefreshActivity } from '@/modules/assets/prices/prices.activity';
import { useFetchPrices } from '@/modules/assets/prices/use-fetch-prices';
import { useHistoricPriceTask } from '@/modules/assets/prices/use-historic-price-task';
import { useOracleCacheTask } from '@/modules/assets/prices/use-oracle-cache-task';
import { usePriceApi } from '@/modules/balances/api/use-price-api';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { Cancelled, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { ExchangeRates } from '@/modules/settings/types/user-settings';
import { useSetting } from '@/modules/settings/use-setting';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { type RunBackendTask, useNativeTask } from '@/modules/task-center/use-native-task';

interface UsePriceTaskManagerReturn {
  /** Reports the outcome as its only message; a cancelled run reports nothing. */
  createOracleCache: (payload: OracleCachePayload) => Promise<Result<void, TaskError>>;
  fetchExchangeRates: (symbol?: SupportedCurrency) => Promise<void>;
  fetchPrices: (payload: FetchPricePayload) => Promise<void>;
  getHistoricPrice: (payload: HistoricPricePayload) => Promise<BigNumber>;
  refreshLatestPrices: (payload: FetchPricePayload, onFetched: () => void) => Promise<void>;
}

export function usePriceTaskManager(): UsePriceTaskManagerReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { submitTask } = useNativeTask();
  const currencySymbol = useSetting('currencySymbol');
  const { exchangeRates } = storeToRefs(useBalancePricesStore());
  const { queryFiatExchangeRates } = usePriceApi();
  const { fetchPrices, queryLatestPrices } = useFetchPrices();
  const { getHistoricPrice } = useHistoricPriceTask();
  const { createOracleCache } = useOracleCacheTask();

  /**
   * The body of an exchange-rate fetch, run through `runTask` inside whichever activity calls it.
   *
   * @remarks
   * The backend answers a rate it could not find with zero rather than an error, so a zero rate
   * fails the activity, which names the currency on its dock row.
   *
   * @param runTask - the runner of the activity this is a stage of
   * @param selectedCurrency - the currency to fetch the rate of
   */
  const queryExchangeRates = async (runTask: RunBackendTask, selectedCurrency: SupportedCurrency): Promise<Result<void, TaskError>> => flatMap(
    await runTask<ExchangeRates>(
      async () => queryFiatExchangeRates([selectedCurrency]),
    ),
    (result) => {
      const rates = ExchangeRates.parse(result);
      set(exchangeRates, {
        ...get(exchangeRates),
        ...rates,
      });

      if (rates[selectedCurrency]?.eq(0))
        return err(TaskFailed({ message: `${t('missing_exchange_rate.title')} (${selectedCurrency})` }));
      return ok(undefined);
    },
  );

  const fetchExchangeRates = async (symbol?: SupportedCurrency): Promise<void> => {
    const selectedCurrency = symbol ?? get(currencySymbol);

    await submitTask({
      id: exchangeRatesActivity.id({ currency: selectedCurrency }),
      kind: exchangeRatesActivity.kind,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => queryExchangeRates(runTask, selectedCurrency),
      subtitle: activityLabelFor(msg.$t('task_center.activity.prices.exchange_rates'), { currency: selectedCurrency }),
      title: t('task_center.group.prices'),
    });
  };

  /**
   * Refreshes the latest prices of `payload.selectedAssets` as one PRICES activity on
   * the price refresh lane, then calls `onFetched` to apply them.
   *
   * @remarks
   * The lane runs one refresh at a time, so two overlapping refreshes cannot race their writes; one
   * asked for while another runs queues behind it, and one asked for again with the same assets
   * and mode joins the first. A queued refresh is the orchestrator's, so a logout drops it.
   *
   * With `ignoreCache` the exchange rates are a first stage of the same activity. A failed rate
   * fetch does not stop the prices, but the activity still reports it. Nothing is applied once
   * the activity is cancelled.
   *
   * Its identity is {@link latestPricesRefreshActivity}, which never joins a plain
   * {@link fetchPrices} of the same set.
   */
  const refreshLatestPrices = async (payload: FetchPricePayload, onFetched: () => void): Promise<void> => {
    const { ignoreCache, selectedAssets } = payload;
    const assetCount = selectedAssets.length;
    await submitTask({
      id: latestPricesRefreshActivity.id(payload),
      kind: latestPricesRefreshActivity.kind,
      lane: latestPricesRefreshActivity.laneOf?.(payload),
      rerunnable: true,
      run: async (context): Promise<Result<void, TaskError>> => {
        const rates = ignoreCache ? await queryExchangeRates(context.runTask, get(currencySymbol)) : ok(undefined);
        const latest = await queryLatestPrices(context, payload);
        if (context.cancelled())
          return err(Cancelled({ message: 'Price refresh cancelled' }));

        onFetched();
        return isErr(latest) ? latest : rates;
      },
      subtitle: activityLabelFor(msg.$t('task_center.activity.prices.latest'), { count: assetCount }, assetCount),
      title: t('task_center.group.prices'),
    });
  };

  return {
    createOracleCache,
    fetchExchangeRates,
    fetchPrices,
    getHistoricPrice,
    refreshLatestPrices,
  };
}
