import type { ComputedRef } from 'vue';
import type { ExchangeFormData } from '@/modules/balances/types/exchanges';
import { useExchangeApi } from '@/modules/balances/api/use-exchange-api';
import { type BinanceAccount, isConnected, savesMissingPairs } from '@/modules/balances/exchanges/binance-pairs-condition';
import { logger } from '@/modules/core/common/logging/logging';
import { isConditionOf, RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

const isMissingPairs = isConditionOf(RaisedConditionKind.BINANCE_PAIRS_MISSING);

interface UseBinancePairsConditionsReturn {
  /** The Binance accounts whose trades are skipped for want of market pairs. */
  accounts: ComputedRef<BinanceAccount[]>;
  /** Settles an account that was just saved with pairs. */
  settleSaved: (form: ExchangeFormData) => void;
  /** Settles every account that is no longer connected, removed or renamed. */
  settleDisconnected: (connected: readonly BinanceAccount[]) => void;
  /** Re-reads each listed account's pairs, settling those that have some now. */
  recheck: () => Promise<void>;
}

/**
 * The Binance accounts reported as missing market pairs, and what settles them.
 *
 * @remarks
 * The backend reports an account whenever a trade history query finds no pairs selected. Saving
 * pairs, removing or renaming the account settles it; a re-check catches pairs saved elsewhere.
 */
export function useBinancePairsConditions(): UseBinancePairsConditionsReturn {
  const store = useRaisedConditionsStore();
  const { conditions } = storeToRefs(store);
  const { queryBinanceUserMarkets } = useExchangeApi();

  const accounts = computed<BinanceAccount[]>(() =>
    get(conditions).filter(isMissingPairs).map(({ location, name }) => ({ location, name })),
  );

  function settle(settles: (account: BinanceAccount) => boolean): void {
    store.clear(condition => isMissingPairs(condition) && settles(condition));
  }

  function settleSaved(form: ExchangeFormData): void {
    settle(account => savesMissingPairs(account, form));
  }

  function settleDisconnected(connected: readonly BinanceAccount[]): void {
    settle(account => !isConnected(account, connected));
  }

  /** Whether the account has pairs now; a failed read keeps it listed. */
  async function hasPairs({ location, name }: BinanceAccount): Promise<boolean> {
    try {
      return (await queryBinanceUserMarkets(name, location)).length > 0;
    }
    catch (error: unknown) {
      logger.error(error);
      return false;
    }
  }

  async function recheck(): Promise<void> {
    const settled = await Promise.all(get(accounts).map(async account => ({ account, done: await hasPairs(account) })));
    const done = settled.filter(({ done }) => done).map(({ account }) => account);
    if (done.length > 0)
      settle(account => isConnected(account, done));
  }

  return { accounts, recheck, settleDisconnected, settleSaved };
}
