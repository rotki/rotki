import type { MessageHandler } from '../interfaces';
import type { MoneriumSessionKeyExpiredData } from '@/modules/core/messaging/types';
import { createConditionalHandler } from '@/modules/core/messaging/utils';
import { useMoneriumOAuth } from '@/modules/integrations/monerium/use-monerium-auth';
import { RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

/**
 * Raises the action center row for an expired Monerium session.
 *
 * @remarks
 * Creates no notification. The status is set to unauthenticated before the refresh rather than left
 * to it: the backend may already have dropped the credentials (`invalid_grant`), and the refresh is
 * a round trip, so without the local write the UI would keep claiming a live session for its
 * duration. The row is raised before the refresh too, so a failed refresh cannot lose it.
 */
export function createMoneriumSessionHandler(): MessageHandler<MoneriumSessionKeyExpiredData> {
  const { refreshStatus, setStatus } = useMoneriumOAuth();
  const { raise } = useRaisedConditionsStore();

  return createConditionalHandler<MoneriumSessionKeyExpiredData>(async () => {
    setStatus({ authenticated: false });
    raise({ kind: RaisedConditionKind.MONERIUM_SESSION });
    await refreshStatus();
    return null;
  });
}
