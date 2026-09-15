import { NotificationGroup, type NotificationGroupKey, notificationGroupOf } from '@rotki/common';
import { createSharedComposable, useSessionStorage } from '@vueuse/core';

const NOTIFICATION_COOLDOWN_MS = 60_000;

/**
 * Groups whose entries are the successive steps of one flow the user just started, rather than
 * repeats of the same condition. Each step replaces the one before it, so the burst cooldown would
 * silence the outcome of an action taken seconds ago: the user would be told the browser is opening
 * and never told whether the authorization worked.
 */
const UNTHROTTLED_GROUPS: Set<NotificationGroup> = new Set([
  NotificationGroup.MONERIUM_AUTH,
]);

export interface UseNotificationCooldownReturn {
  shouldSuppress: (group: NotificationGroupKey) => boolean;
  recordDisplay: (group: NotificationGroupKey) => void;
}

function isUnthrottled(group: NotificationGroupKey): boolean {
  const name = notificationGroupOf(group);
  return name !== undefined && UNTHROTTLED_GROUPS.has(name);
}

/**
 * Decides whether a grouped notification may interrupt the user, so one query run does not toast
 * the same group repeatedly.
 *
 * @remarks
 * Lives in session storage, since it is only about the current run: a condition that outlives the
 * session is an action center row, not a notification. Shared, so that a display recorded by the
 * store is visible to the dispatcher at once.
 */
export const useNotificationCooldown = createSharedComposable((): UseNotificationCooldownReturn => {
  const lastDisplay: Ref<Record<string, number>> = useSessionStorage('rotki.notification.last_display', {});

  function shouldSuppress(group: NotificationGroupKey): boolean {
    if (isUnthrottled(group))
      return false;

    const lastTime = get(lastDisplay)[group] ?? 0;
    return Date.now() - lastTime < NOTIFICATION_COOLDOWN_MS;
  }

  function recordDisplay(group: NotificationGroupKey): void {
    set(lastDisplay, {
      ...get(lastDisplay),
      [group]: Date.now(),
    });
  }

  return { recordDisplay, shouldSuppress };
});
