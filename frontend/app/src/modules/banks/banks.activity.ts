import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { EXCHANGE_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { ActivityKind } from '@/modules/task-center/core/types';

/** Loading the balances of every bank connection, as one request on the exchange lane. */
export const bankBalancesActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.BANK_BALANCES,
  lane: () => EXCHANGE_LANE,
});
