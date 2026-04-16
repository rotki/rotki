import type { StateHandler } from '@/modules/core/messaging/interfaces';
import type { NegativeBalanceDetectedData } from '@/modules/core/messaging/types/status-types';
import { createStateHandler } from '@/modules/core/messaging/utils';
import { useHistoricalBalancesStore } from '@/modules/history/balances/use-historical-balances-store';

export function createNegativeBalanceDetectedHandler(): StateHandler<NegativeBalanceDetectedData> {
  const { addNegativeBalance } = useHistoricalBalancesStore();

  return createStateHandler<NegativeBalanceDetectedData>((data) => {
    addNegativeBalance(data);
  });
}
