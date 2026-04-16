import type { MessageHandlerRegistry } from './interfaces';
import { createBusinessRegistry } from './registries/business-registry';
import { createNotificationRegistry } from './registries/notification-registry';
import { createStatusRegistry } from './registries/status-registry';

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
  ) as MessageHandlerRegistry;
}
