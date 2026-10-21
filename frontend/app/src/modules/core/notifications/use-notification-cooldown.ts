import { NotificationGroup } from '@rotki/common';
import { createSharedComposable, useSessionStorage } from '@vueuse/core';

const NOTIFICATION_COOLDOWN_MS = 60_000;

/**
 * Groups that arrive in bursts of one announcement: tokens detected one after another during a
 * single query. Only these are throttled, one popup per group per cooldown.
 *
 * @remarks
 * Every other group pops each time it should. A backend problem never pops, a condition is an
 * action center row, and a group whose entries are the steps of a flow the user just started (such
 * as Monerium's authorization) must not have its outcome silenced by the step before it.
 */
const THROTTLED_GROUPS: ReadonlySet<NotificationGroup> = new Set([
  NotificationGroup.NEW_DETECTED_TOKENS,
]);

export interface UseNotificationCooldownReturn {
  shouldSuppress: (group: NotificationGroup) => boolean;
  recordDisplay: (group: NotificationGroup) => void;
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

  function shouldSuppress(group: NotificationGroup): boolean {
    if (!THROTTLED_GROUPS.has(group))
      return false;

    const lastTime = get(lastDisplay)[group] ?? 0;
    return Date.now() - lastTime < NOTIFICATION_COOLDOWN_MS;
  }

  function recordDisplay(group: NotificationGroup): void {
    set(lastDisplay, {
      ...get(lastDisplay),
      [group]: Date.now(),
    });
  }

  return { recordDisplay, shouldSuppress };
});
