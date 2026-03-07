import { useBalanceWatchers } from '@/modules/balances/use-balance-watchers';
import { useHistoryWatchers } from '@/modules/history/use-history-watchers';

export function useMonitorWatchers(): void {
  useBalanceWatchers();
  useHistoryWatchers();
}
