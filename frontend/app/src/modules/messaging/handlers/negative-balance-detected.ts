import type { StateHandler } from '../interfaces';
import type { NegativeBalanceDetectedData } from '../types/status-types';
import { useHistoricalBalancesStore } from '@/modules/history/balances/store';
import { createStateHandler } from '@/modules/messaging/utils';

export function createNegativeBalanceDetectedHandler(): StateHandler<NegativeBalanceDetectedData> {
  const { addNegativeBalance } = useHistoricalBalancesStore();

  return createStateHandler<NegativeBalanceDetectedData>((data) => {
    addNegativeBalance(data);
  });
}
