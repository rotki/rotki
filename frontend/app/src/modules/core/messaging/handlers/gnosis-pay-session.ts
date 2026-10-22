import type { MessageHandler } from '../interfaces';
import type { GnosisPaySessionKeyExpiredData } from '@/modules/core/messaging/types';
import { createConditionalHandler } from '@/modules/core/messaging/utils';
import { RaisedConditionKind, sessionCauseOf, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

/**
 * Raises the action center row for a Gnosis Pay session that is missing or expired.
 *
 * @remarks
 * Creates no notification. No route reports whether a session is valid, so the row stays raised
 * until a sign-in is verified, which is what clears it. A reminder sent on each redecode replaces
 * the row rather than adding one.
 */
export function createGnosisPaySessionHandler(): MessageHandler<GnosisPaySessionKeyExpiredData> {
  const { raise } = useRaisedConditionsStore();

  return createConditionalHandler<GnosisPaySessionKeyExpiredData>((data) => {
    raise({ cause: sessionCauseOf(data.reason), kind: RaisedConditionKind.GNOSIS_PAY_SESSION });
    return null;
  });
}
