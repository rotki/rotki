import type { MessageHandler } from '../interfaces';
import type { MissingApiKey } from '@/modules/core/messaging/types';
import { createConditionalHandler } from '@/modules/core/messaging/utils';
import { SuppressibleMissingKeyService } from '@/modules/settings/types/user-settings';
import { RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

/**
 * Raises the action center row for a service whose key a query asked for.
 *
 * @remarks
 * Creates no notification: the row is the only place a missing key is shown, and it leaves once a
 * key is saved for the service. The backend already skips the services the user suppressed.
 * Blockscout also reports a saved key it refused (`key_not_usable`), which the row must not answer
 * by asking for a key that already exists.
 */
export function createMissingApiKeyHandler(): MessageHandler<MissingApiKey> {
  const { raise } = useRaisedConditionsStore();

  return createConditionalHandler<MissingApiKey>(({ location, reason, service }) => {
    const keyRejected = service === SuppressibleMissingKeyService.BLOCKSCOUT && reason === 'key_not_usable';
    raise({ kind: RaisedConditionKind.MISSING_API_KEY, location, service, ...(keyRejected ? { keyRejected } : {}) });
    return null;
  });
}
