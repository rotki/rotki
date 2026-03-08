import { useBalanceWatchers } from '@/modules/balances/use-balance-watchers';
import { useHistoryWatchers } from '@/modules/history/use-history-watchers';
import { useEthValidatorWatchers } from '@/modules/staking/eth/composables/use-eth-validator-watchers';
import { useStatisticsWatchers } from '@/modules/statistics/use-statistics-watchers';

export function useMonitorWatchers(): void {
  useBalanceWatchers();
  useHistoryWatchers();
  useStatisticsWatchers();
  useEthValidatorWatchers();
}
