import type { MessageHandler } from '../interfaces';
import type { OraclePenalizedData } from '@/modules/core/messaging/types';
import { createConditionalHandler } from '@/modules/core/messaging/utils';
import { isConditionOf, RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

const MS_PER_SECOND = 1000;

const isPenalized = isConditionOf(RaisedConditionKind.ORACLE_PENALIZED);

/**
 * Raises the action center row of an oracle the backend set aside, because it stopped answering
 * (`timeout`) or kept failing (`errors`), for the penalty duration.
 *
 * @remarks
 * Creates no notification: rotki uses the other oracles meanwhile and the oracle again once the
 * penalty runs out, so there is nothing the user has to do. The row explains a price load that
 * suddenly leans on the other oracles, one per oracle, and leaves when the penalty ends. A penalty
 * the backend held while no client was connected raises nothing once it has run out.
 */
export function createOraclePenalizedHandler(): MessageHandler<OraclePenalizedData> {
  const { clear, raise } = useRaisedConditionsStore();

  function clearExpired(oracle: string): void {
    clear(condition => isPenalized(condition) && condition.oracle === oracle && condition.until <= Date.now());
  }

  return createConditionalHandler<OraclePenalizedData>(({ oracle, penaltyDuration, reason }, { lastSent }) => {
    const until = (lastSent ?? new Date()).getTime() + penaltyDuration * MS_PER_SECOND;
    const remaining = until - Date.now();
    if (remaining <= 0)
      return;

    raise({ kind: RaisedConditionKind.ORACLE_PENALIZED, oracle, reason, until });
    setTimeout(clearExpired, remaining, oracle);
  });
}
