import type { ComputedRef } from 'vue';
import { isConnected } from '@/modules/balances/exchanges/binance-pairs-condition';
import { isConditionOf, RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

/** A connected exchange account: `name` is the user's name for it on `location`. */
interface ExchangeAccount {
  location: string;
  name: string;
}

const isKeyRejected = isConditionOf(RaisedConditionKind.EXCHANGE_KEY_REJECTED);

interface UseExchangeKeyConditionsReturn {
  /** The connected exchange accounts whose key the exchange refused. */
  accounts: ComputedRef<ExchangeAccount[]>;
  /** Settles an account that was just saved. */
  settleSaved: (account: ExchangeAccount) => void;
  /** Settles every account that is no longer connected, removed or renamed. */
  settleDisconnected: (connected: readonly ExchangeAccount[]) => void;
}

/**
 * The exchange accounts whose key the exchange refused, and what settles them.
 *
 * @remarks
 * The backend reports an account when a query is refused for its key, such as one missing a
 * permission. Saving the account settles it, since a new key or a permission fixed on the exchange
 * is only tried by the next query, which reports the account again if it is still refused.
 * Removing or renaming the account settles it too.
 */
export function useExchangeKeyConditions(): UseExchangeKeyConditionsReturn {
  const store = useRaisedConditionsStore();
  const { conditions } = storeToRefs(store);

  const accounts = computed<ExchangeAccount[]>(() =>
    get(conditions).filter(isKeyRejected).map(({ location, name }) => ({ location, name })),
  );

  function settleSaved(account: ExchangeAccount): void {
    store.clear(condition => isKeyRejected(condition) && isConnected(condition, [account]));
  }

  function settleDisconnected(connected: readonly ExchangeAccount[]): void {
    store.clear(condition => isKeyRejected(condition) && !isConnected(condition, connected));
  }

  return { accounts, settleDisconnected, settleSaved };
}
