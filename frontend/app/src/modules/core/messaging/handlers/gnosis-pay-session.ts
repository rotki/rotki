import type { MessageHandler } from '../interfaces';
import type { GnosisPaySessionKeyExpiredData } from '@/modules/core/messaging/types';
import { createConditionalHandler } from '@/modules/core/messaging/utils';
import { RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

/**
 * Raises the action center row for an expired Gnosis Pay session.
 *
 * @remarks
 * Creates no notification. No route reports whether a session is valid, so the row stays raised
 * until a sign-in is verified, which is what clears it.
 */
export function createGnosisPaySessionHandler(): MessageHandler<GnosisPaySessionKeyExpiredData> {
  const { raise } = useRaisedConditionsStore();

  return createConditionalHandler<GnosisPaySessionKeyExpiredData>(() => {
    raise({ kind: RaisedConditionKind.GNOSIS_PAY_SESSION });
    return null;
  });
}
