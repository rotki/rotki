import { type NotificationData, Priority } from '@rotki/common';
import { orderBy } from 'es-toolkit';
import { useNotificationCooldown } from '@/modules/core/notifications/use-notification-cooldown';

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

  /**
   * The notifications only the user can resolve, which is what the badge counts.
   *
   * @remarks
   * Deliberately not "everything unread". Since the legacy lane stopped interrupting, the drawer
   * carries the ~190 backend strings silently, and counting those would rebuild the uninformative
   * number the badge used to show. This stays outstanding until the row goes away, because opening
   * the drawer does not resolve the condition behind it.
   */
  const actionRequired = computed<NotificationData[]>(
    () => get(data).filter(notification => notification.priority === Priority.ACTION),
  );

  /** Whether anything has arrived since the drawer was last opened, which drives the dot. */
  const hasUnread = computed<boolean>(() => get(data).some(notification => !notification.read));

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
    if (ids.length === 0)
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
   * Marks everything currently stored as seen, which the drawer does when it opens.
   *
   * @remarks
   * Everything, not the rows scrolled past: the dot answers "is there anything new", so partial
   * precision would buy nothing and leave the dot lit after the user has looked.
   */
  function markAllRead(): void {
    if (!get(hasUnread))
      return;

    replace(get(data).map(notification => notification.read ? notification : { ...notification, read: true }));
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
    actionRequired,
    add,
    count,
    data,
    displayed,
    getNextId,
    hasUnread,
    markAllRead,
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
