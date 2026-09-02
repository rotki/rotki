import type { NotificationCategory } from '@rotki/common';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';

interface UseServiceKeyNotificationsReturn {
  dismissCategory: (category: NotificationCategory) => void;
  dismissNamedService: (service: string) => void;
}

/**
 * Dismisses the notification that asked for a service's api key, once that key is saved.
 *
 * @remarks
 * Both lookups read the prioritized list rather than the full one. Actionable notifications sort to
 * the front of it, so the one being dismissed is reached without walking everything the session has
 * accumulated.
 *
 * @returns the two ways a service is named: by its own notification category, or by the service
 * name a shared category's notification carries as an i18n param
 */
export function useServiceKeyNotifications(): UseServiceKeyNotificationsReturn {
  const store = useNotificationsStore();

  /**
   * Dismisses every notification filed under a category of its own.
   *
   * @remarks
   * All of them, not the first: a service asked repeatedly over a session leaves one notification
   * per attempt, and the key now covers them all.
   *
   * @param category - the one a single service owns outright
   */
  function dismissCategory(category: NotificationCategory): void {
    for (const notification of store.prioritized.filter(data => data.category === category))
      store.remove(notification.id);
  }

  /**
   * Dismisses the notification a shared category carries for one named service.
   *
   * @remarks
   * The category cannot separate them, so the service name is read from the i18n param the message
   * interpolates. Matched case-insensitively, since that param is the display name.
   *
   * @param service - the lowercase service key, as `useApiKey` names it
   */
  function dismissNamedService(service: string): void {
    const notification = store.prioritized.find(data => data.i18nParam?.props?.service.toLowerCase() === service);
    if (notification)
      store.remove(notification.id);
  }

  return { dismissCategory, dismissNamedService };
}
