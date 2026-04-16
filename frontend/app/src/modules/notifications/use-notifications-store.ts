import { type NotificationData, Priority } from '@rotki/common';
import { orderBy } from 'es-toolkit';
import { useNotificationCooldown } from '@/modules/notifications/use-notification-cooldown';

const NOTIFICATION_MAX_SIZE = 200;

function take(notifications: NotificationData[], n: number = NOTIFICATION_MAX_SIZE): NotificationData[] {
  return orderBy(notifications, ['date'], ['desc']).slice(0, n);
}

export const useNotificationsStore = defineStore('notifications', () => {
  const data = shallowRef<NotificationData[]>([]);
  const messageOverflow = ref<boolean>(false);
  const cooldown = useNotificationCooldown();

  let nextId = 1;

  function getNextId(): number {
    return nextId++;
  }

  const prioritized = computed<NotificationData[]>(() => {
    const byDate = orderBy(get(data), ['date'], ['desc']);
    return orderBy(byDate, [(n: NotificationData): Priority => n.priority ?? Priority.NORMAL], ['desc']);
  });

  const count = computed<number>(() => get(data).length);

  const queue = computed<NotificationData[]>(() => get(prioritized).filter(notification => notification.display));

  function add(payload: NotificationData[]): void {
    set(data, take([...get(data), ...payload]));
  }

  function replace(notifications: NotificationData[]): void {
    set(data, take(notifications));
  }

  function remove(id: number): void {
    const notifications = [...get(data)];
    const index = notifications.findIndex(v => v.id === id);
    if (index > -1)
      notifications.splice(index, 1);

    set(data, notifications);
    set(messageOverflow, false);
  }

  function removeMatching(predicate: (notification: NotificationData) => boolean): void {
    const match = get(data).find(predicate);
    if (match !== undefined)
      remove(match.id);
  }

  function displayed(ids: number[]): void {
    if (ids.length <= 0)
      return;

    const notifications = [...get(data)];
    for (const id of ids) {
      const index = notifications.findIndex(({ id: idA }) => idA === id);
      if (index < 0)
        continue;

      const notification = notifications[index];
      if (notification.group)
        cooldown.recordDisplay(notification.group);

      notifications[index] = { ...notification, display: false };
    }
    replace(notifications);
  }

  /**
   * Return a mutable copy of the current notifications, trimmed to leave room for one new entry.
   * Used by the dispatcher to provide a working copy to strategies.
   */
  function trimmedCopy(): NotificationData[] {
    const notifications = [...get(data)];
    const trimmed = take(notifications, NOTIFICATION_MAX_SIZE - 1);
    set(messageOverflow, notifications.length > trimmed.length);
    return trimmed;
  }

  return {
    add,
    count,
    data,
    displayed,
    getNextId,
    messageOverflow,
    prioritized,
    queue,
    remove,
    removeMatching,
    replace,
    trimmedCopy,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useNotificationsStore, import.meta.hot));
