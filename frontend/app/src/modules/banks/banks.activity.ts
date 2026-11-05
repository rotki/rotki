import type { ConnectionRef } from '@/modules/core/common/connection';
import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { BANK_BALANCES_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { ActivityKind } from '@/modules/task-center/core/types';

/** Loading the balances of every bank connection, as one request. */
export const bankBalancesActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.BANK_BALANCES,
  lane: () => BANK_BALANCES_LANE,
});

/**
 * Loading the balances of one bank connection, keyed by its stable identifier.
 *
 * @remarks
 * Kept apart from {@link bankBalancesActivity} so a bank refreshed on its own, for example to answer
 * its TAN, neither joins nor waits on a refresh of every bank.
 */
export const bankConnectionBalancesActivity = defineActivity<ConnectionRef, readonly [string]>({
  key: subject => [subject.identifier],
  kind: ActivityKind.BANK_BALANCES,
  lane: () => BANK_BALANCES_LANE,
});
