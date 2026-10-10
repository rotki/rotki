import type { ComputedRef, Ref } from 'vue';
import type { HyperliquidStakingSummary } from '@/modules/staking/staking-types';
import { type BigNumber, Zero } from '@rotki/common';
import { useHyperliquidStakingApi } from '@/modules/staking/api/use-hyperliquid-staking-api';

export interface HyperliquidStakingRow extends HyperliquidStakingSummary {
  address: string;
}

interface UseHyperliquidStakingReturn {
  error: Readonly<Ref<string>>;
  loading: Readonly<Ref<boolean>>;
  refresh: () => Promise<void>;
  rows: ComputedRef<HyperliquidStakingRow[]>;
  total: ComputedRef<HyperliquidStakingSummary>;
}

function sumOf(rows: HyperliquidStakingRow[], key: keyof HyperliquidStakingSummary): BigNumber {
  return rows.reduce<BigNumber>((acc, row) => acc.plus(row[key]), Zero);
}

/**
 * Loads the core staking account of every tracked Hyperliquid address.
 *
 * @remarks
 * A failed query keeps the rows of the last successful one and reports the failure through
 * `error`, so a flaky API does not blank a table the user was reading.
 */
export function useHyperliquidStaking(): UseHyperliquidStakingReturn {
  const { fetchStakingSummaries } = useHyperliquidStakingApi();

  const rows = shallowRef<HyperliquidStakingRow[]>([]);
  const loading = shallowRef<boolean>(false);
  const error = shallowRef<string>('');

  const total = computed<HyperliquidStakingSummary>(() => ({
    delegated: sumOf(get(rows), 'delegated'),
    pendingWithdrawal: sumOf(get(rows), 'pendingWithdrawal'),
    undelegated: sumOf(get(rows), 'undelegated'),
  }));

  async function refresh(): Promise<void> {
    set(loading, true);
    set(error, '');
    try {
      const summaries = await fetchStakingSummaries();
      set(rows, Object.entries(summaries).map(([address, summary]) => ({ ...summary, address })));
    }
    catch (error_: unknown) {
      set(error, error_ instanceof Error ? error_.message : String(error_));
    }
    finally {
      set(loading, false);
    }
  }

  return {
    error: readonly(error),
    loading: readonly(loading),
    refresh,
    rows: computed<HyperliquidStakingRow[]>(() => get(rows)),
    total,
  };
}
