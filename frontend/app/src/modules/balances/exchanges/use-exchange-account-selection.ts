import type { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter, WritableComputedRef } from 'vue';
import type { Exchange } from '@/modules/balances/types/exchanges';
import { startPromise } from '@shared/utils';
import { useValueThreshold } from '@/modules/assets/amount-display/use-usd-value-threshold';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { bigNumberSum, calculatePercentage } from '@/modules/core/common/data/calculation';
import { firstQueryValue } from '@/modules/core/table/route';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';

export interface ExchangeAccountOption {
  identifier: string;
  name: string;
  value: BigNumber;
  /** The account's percentage of the exchange's total, as `calculatePercentage` formats it. */
  share: string;
  /** Why the account's last refresh failed, so its figures are from an earlier one, if it has any. */
  error?: string;
  /** Whether any refresh of the account has succeeded, so its value is known rather than missing. */
  loaded: boolean;
}

interface UseExchangeAccountSelectionReturn {
  /** The exchange's connections to choose between, largest first, empty unless it has more than one. */
  accounts: ComputedRef<ExchangeAccountOption[]>;
  /** The chosen connection, or undefined for all of them together. */
  picked: ComputedRef<ExchangeAccountOption | undefined>;
  /** The identifier of the chosen connection, or undefined for all of them together. */
  modelAccount: WritableComputedRef<string | undefined>;
  /** The chosen connection's balances, or undefined when no connection is chosen. */
  accountBalances: ComputedRef<AssetBalanceWithPrice[] | undefined>;
}

/** The route query key that carries the chosen connection, so a reload or a link keeps it. */
const ACCOUNT_QUERY = 'account';

/**
 * Picks one connection of an exchange so the page can show that account's balances alone.
 *
 * @param exchange - the exchange in view; without one there is nothing to pick
 */
export function useExchangeAccountSelection(exchange: MaybeRefOrGetter<string | undefined>): UseExchangeAccountSelectionReturn {
  const route = useRoute();
  const router = useRouter();

  const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
  const { exchangeAccountBalances, exchangeFailedAccounts } = storeToRefs(useBalancesStore());
  const { getExchangeAccountBalances } = useAggregatedBalances();

  const valueThreshold = useValueThreshold(BalanceSource.EXCHANGES);

  /**
   * One connection's balances above the exchanges' hide-small-balances threshold.
   *
   * @remarks
   * The backend applies the threshold to each exchange's totals but reports every account in full,
   * so the same rule is applied here to keep an account's figures consistent with the exchange's.
   */
  function visibleBalances(location: string, identifier: string): AssetBalanceWithPrice[] {
    const threshold = get(valueThreshold);
    const balances = getExchangeAccountBalances(location, identifier);
    return threshold === undefined ? balances : balances.filter(balance => balance.value.gt(threshold));
  }

  /** The connections of the exchange in view. */
  const connections = computed<Exchange[]>(() => {
    const location = toValue(exchange);
    return location ? get(connectedExchanges).filter(connection => connection.location === location) : [];
  });

  /** The visible balances of each connection of the exchange in view, by connection identifier. */
  const balancesByAccount = computed<Map<string, AssetBalanceWithPrice[]>>(() =>
    new Map(get(connections).map(({ identifier, location }) => [identifier, visibleBalances(location, identifier)])));

  const accounts = computed<ExchangeAccountOption[]>(() => {
    const location = toValue(exchange);
    const options = get(connections);
    if (!location || options.length < 2)
      return [];

    const balances = get(balancesByAccount);
    const failed = get(exchangeFailedAccounts)[location] ?? {};
    const stored = get(exchangeAccountBalances)[location] ?? {};
    const totals = options.map(({ identifier, name }) => ({
      error: failed[identifier],
      identifier,
      loaded: identifier in stored,
      name,
      value: bigNumberSum((balances.get(identifier) ?? []).map(balance => balance.value)),
    }));
    const total = bigNumberSum(totals.map(({ value }) => value));
    return totals
      .map(account => ({ ...account, share: calculatePercentage(account.value, total) }))
      .sort((a, b) => b.value.comparedTo(a.value) ?? 0);
  });

  /**
   * The connection the route query names, when the exchange in view offers it.
   *
   * @remarks
   * A query naming anything else (a removed connection, another exchange's, or one that has not
   * loaded yet) reads as all accounts and is left in place, so a reload keeps the pick once the
   * connections arrive.
   */
  const picked = computed<ExchangeAccountOption | undefined>(() => {
    const account = firstQueryValue(get(route).query[ACCOUNT_QUERY]);
    return get(accounts).find(option => option.identifier === account);
  });

  const modelAccount = computed<string | undefined>({
    get: () => get(picked)?.identifier,
    set: (account) => {
      const query = { ...get(route).query, [ACCOUNT_QUERY]: account };
      if (!account)
        delete query[ACCOUNT_QUERY];
      startPromise(router.replace({ query }));
    },
  });

  const accountBalances = computed<AssetBalanceWithPrice[] | undefined>(() => {
    const identifier = get(modelAccount);
    return identifier ? get(balancesByAccount).get(identifier) : undefined;
  });

  return {
    accountBalances,
    accounts,
    modelAccount,
    picked,
  };
}
