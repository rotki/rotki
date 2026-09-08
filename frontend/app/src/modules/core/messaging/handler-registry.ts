import type { MessageHandlerRegistry } from './interfaces';
import { createBusinessRegistry } from './registries/business-registry';
import { createNotificationRegistry } from './registries/notification-registry';
import { createStatusRegistry } from './registries/status-registry';

/**
 * Builds the handler for every socket message type.
 *
 * @remarks
 * Call this from a setup context. Every `create*Handler` below it resolves its stores and
 * composables while it is being built, then closes over them, so the handlers themselves can run
 * later from a socket callback where no active component instance exists. Building the registry
 * outside setup fails at that resolution instead, before any message arrives.
 */
export function createHandlerRegistry(
  t: ReturnType<typeof useI18n>['t'],
  router: ReturnType<typeof useRouter>,
): MessageHandlerRegistry {
  const statusRegistry = createStatusRegistry(t);
  const notificationRegistry = createNotificationRegistry(t, router);
  const businessRegistry = createBusinessRegistry(t, router);

  return Object.assign(
    {},
    statusRegistry,
    notificationRegistry,
    businessRegistry,
  );
}
