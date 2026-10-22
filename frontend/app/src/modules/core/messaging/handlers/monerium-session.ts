import type { MessageHandler } from '../interfaces';
import type { MoneriumSessionKeyExpiredData } from '@/modules/core/messaging/types';
import { createConditionalHandler } from '@/modules/core/messaging/utils';
import { useMoneriumOAuth } from '@/modules/integrations/monerium/use-monerium-auth';
import { RaisedConditionKind, sessionCauseOf, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

/**
 * Raises the action center row for a Monerium session that is missing or expired.
 *
 * @remarks
 * Creates no notification. On an expiry the status is set to unauthenticated before the refresh
 * rather than left to it: the backend may already have dropped the credentials (`invalid_grant`),
 * and the refresh is a round trip, so without the local write the UI would keep claiming a live
 * session for its duration. The row is raised before the refresh too, so a failed refresh cannot
 * lose it. A reminder is sent while the user is already signed out, so it only raises the row.
 */
export function createMoneriumSessionHandler(): MessageHandler<MoneriumSessionKeyExpiredData> {
  const { refreshStatus, setStatus } = useMoneriumOAuth();
  const { raise } = useRaisedConditionsStore();

  return createConditionalHandler<MoneriumSessionKeyExpiredData>(async (data) => {
    if (!data.reminder)
      setStatus({ authenticated: false });
    raise({ cause: sessionCauseOf(data.reason), kind: RaisedConditionKind.MONERIUM_SESSION });
    if (!data.reminder)
      await refreshStatus();
    return null;
  });
}
