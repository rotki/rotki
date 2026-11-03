import type { AssetBalanceWithPriceAndChains, BigNumber } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { BankConnection, BankConnectionIdentity } from '@/modules/banks/types';
import { BankConnectionState, bankConnectionState } from '@/modules/banks/bank-connection-state';
import { type BankBalanceData, useBankData } from '@/modules/banks/use-bank-data';
import { useBanks } from '@/modules/banks/use-banks';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseBankBalancesPageReturn {
  banks: ComputedRef<BankBalanceData[]>;
  /** The bank the page shows, or none when it shows all of them or names one that is gone. */
  selectedBank: ComputedRef<BankBalanceData | undefined>;
  /** What the table lists: the selected bank's holdings, or every bank's together. */
  balances: ComputedRef<AssetBalanceWithPriceAndChains[]>;
  /** The connections in view that need the user, a pending TAN first. */
  issues: ComputedRef<BankConnection[]>;
  total: ComputedRef<BigNumber>;
  /** Whether every bank is being queried; a bank refreshed on its own shows through {@link isBankLoading}. */
  loading: ComputedRef<boolean>;
  isBankLoading: (name: string) => boolean;
  refreshAll: () => Promise<void>;
  refreshBank: (connection: BankConnectionIdentity) => Promise<void>;
  /** The page's Refresh: the bank in view, or every bank when the page shows them all. */
  refreshInView: () => Promise<void>;
}

/** Which connection needs the user first; a connection that is fine needs nothing. */
const STATE_RANK: Readonly<Record<BankConnectionState, number | undefined>> = {
  [BankConnectionState.AUTHENTICATION]: 0,
  [BankConnectionState.EXPIRED]: 1,
  [BankConnectionState.FAILED]: 2,
  [BankConnectionState.OK]: undefined,
};

/**
 * The bank balances page: every bank connection together, or the one the route names.
 *
 * @param selected - the name of the connection in the route, if any; names are unique across banks
 */
export function useBankBalancesPage(selected: MaybeRefOrGetter<string | undefined>): UseBankBalancesPageReturn {
  const { allBalances, banks, total } = useBankData();
  const { fetchBankBalances, refreshBankConnections } = useBanks();
  const { useIsActive } = useTaskCenter();

  /** The banks this page is refreshing on their own. */
  const refreshing = ref<Set<string>>(new Set());

  const loading = useIsActive(ActivityKind.BANK_BALANCES);

  const selectedBank = computed<BankBalanceData | undefined>(() => {
    const name = toValue(selected);
    return name === undefined ? undefined : get(banks).find(bank => bank.name === name);
  });

  const balances = computed<AssetBalanceWithPriceAndChains[]>(() => get(selectedBank)?.balances ?? get(allBalances));

  const issues = computed<BankConnection[]>(() => {
    const current = get(selectedBank);
    return (current ? [current] : get(banks))
      .flatMap((bank) => {
        const rank = STATE_RANK[bankConnectionState(bank)];
        return rank === undefined ? [] : [{ bank, rank }];
      })
      .sort((a, b) => a.rank - b.rank)
      .map(({ bank }) => bank);
  });

  /** A tile spins while every bank is queried, or while this page refreshes its bank alone. */
  function isBankLoading(name: string): boolean {
    return get(loading) || get(refreshing).has(name);
  }

  async function refreshAll(): Promise<void> {
    await refreshBankConnections();
    await fetchBankBalances(true);
  }

  async function refreshBank({ connector, name }: BankConnectionIdentity): Promise<void> {
    set(refreshing, new Set([...get(refreshing), name]));
    try {
      await fetchBankBalances(true, { connector, name });
    }
    finally {
      set(refreshing, new Set([...get(refreshing)].filter(entry => entry !== name)));
    }
  }

  async function refreshInView(): Promise<void> {
    const current = get(selectedBank);
    if (current)
      await refreshBank(current);
    else
      await refreshAll();
  }

  return {
    balances,
    banks,
    isBankLoading,
    issues,
    loading,
    refreshAll,
    refreshBank,
    refreshInView,
    selectedBank,
    total,
  };
}
