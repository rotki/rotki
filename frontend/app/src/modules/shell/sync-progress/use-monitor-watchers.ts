import { useBalanceWatchers } from '@/modules/balances/use-balance-watchers';
import { useHistoryWatchers } from '@/modules/history/use-history-watchers';
import { usePremiumWatchers } from '@/modules/premium/use-premium-watchers';
import { useEthValidatorWatchers } from '@/modules/staking/eth/use-eth-validator-watchers';
import { useStatisticsWatchers } from '@/modules/statistics/use-statistics-watchers';

export function useMonitorWatchers(): void {
  useBalanceWatchers();
  useHistoryWatchers();
  usePremiumWatchers();
  useStatisticsWatchers();
  useEthValidatorWatchers();
}
