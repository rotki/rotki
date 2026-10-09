import type { MessageHandler } from '../interfaces';
import { startPromise } from '@shared/utils';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useBackendProblemsStore } from '@/modules/core/notifications/problems/use-backend-problems-store';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import {
  PremiumInactiveCause,
  RaisedConditionKind,
  useRaisedConditionsStore,
} from '@/modules/shell/action-center/use-raised-conditions-store';
import { type UserMessageData, UserMessageKey } from '../types/base';
import { createConditionalHandler } from '../utils/handler-factories';

/** The AuthFailure service the backend names for rotki's own premium credentials. */
const ROTKI_PREMIUM_SERVICE = 'rotki_premium';

type AuthFields = Extract<UserMessageData, { key: typeof UserMessageKey.AUTH }>['fields'];

/**
 * Files a backend `add_error` / `add_warning` user message. It never creates a notification.
 *
 * @remarks
 * Rejected credentials raise the action center row that asks for the fix, since only the user can
 * fix them. Premium credentials raise the premium row, an exchange account's the row for that
 * account, and any other service's the missing key row, which stays while the service has no key.
 *
 * Every other family is a backend problem: filed in the drawer's tree under its family and
 * location, as one item per backend `group`, and never popped. The bulk of the corpus is
 * self-describing as ignorable ("Ignoring it", "Skipping balance result"), and a condition that
 * warrants an interrupt earns it by getting a structured message type, not by being a longer
 * string.
 */
export function createUserMessageHandler(): MessageHandler<UserMessageData> {
  const { allExchanges } = storeToRefs(useLocationStore());
  const { raise } = useRaisedConditionsStore();
  const { record } = useBackendProblemsStore();

  function raiseRejectedCredentials({ account, service }: AuthFields): void {
    if (service === ROTKI_PREMIUM_SERVICE)
      raise({ cause: PremiumInactiveCause.EXPIRED, kind: RaisedConditionKind.PREMIUM_INACTIVE });
    else if (account && get(allExchanges).includes(service))
      raise({ kind: RaisedConditionKind.EXCHANGE_KEY_REJECTED, location: service, name: account });
    else
      raiseRemovedServiceKey(service);
  }

  /**
   * Raises the missing key row of an external service whose key the backend refused.
   *
   * @remarks
   * The backend deletes such a key before it reports it (beaconcha.in), while the saved keys are
   * only loaded at login. The row stays closed while a key looks saved, so the keys are reloaded
   * for it to open.
   */
  function raiseRemovedServiceKey(service: string): void {
    raise({ kind: RaisedConditionKind.MISSING_API_KEY, service });
    startPromise(useExternalApiKeys().load());
  }

  return createConditionalHandler<UserMessageData>((data, { count, lastSent }) => {
    if (data.key === UserMessageKey.AUTH)
      raiseRejectedCredentials(data.fields);
    else
      record({ at: lastSent ?? new Date(), count, identity: JSON.stringify(data.group), source: data });

    return null;
  });
}
