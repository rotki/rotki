import type { HyperliquidStakingSummary } from '@/modules/staking/staking-types';
import { type BigNumber, Zero } from '@rotki/common';
import { useStakingApi } from '@/modules/staking/api/use-staking-api';
import { useStakingRows, type UseStakingRowsReturn } from '@/modules/staking/use-staking-rows';

export interface HyperliquidStakingRow extends HyperliquidStakingSummary {
  address: string;
}

type UseHyperliquidStakingReturn = UseStakingRowsReturn<HyperliquidStakingRow, HyperliquidStakingSummary>;

function sumOf(rows: HyperliquidStakingRow[], key: keyof HyperliquidStakingSummary): BigNumber {
  return rows.reduce<BigNumber>((acc, row) => acc.plus(row[key]), Zero);
}

/** Loads the core staking account of every tracked Hyperliquid address. */
export function useHyperliquidStaking(): UseHyperliquidStakingReturn {
  const { fetchHyperliquidStakingSummaries } = useStakingApi();

  return useStakingRows({
    fetch: fetchHyperliquidStakingSummaries,
    toRows: summaries => Object.entries(summaries).map(([address, summary]) => ({ ...summary, address })),
    toTotal: rows => ({
      delegated: sumOf(rows, 'delegated'),
      pendingWithdrawal: sumOf(rows, 'pendingWithdrawal'),
      undelegated: sumOf(rows, 'undelegated'),
    }),
  });
}
