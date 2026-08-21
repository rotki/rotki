import type { NotificationScheduleEntry } from '@/modules/settings/types/frontend-settings';
import { NotificationGroup, type NotificationGroupKey, notificationGroupOf } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { createSharedComposable, useSessionStorage } from '@vueuse/core';
import { isEmpty } from 'es-toolkit/compat';
import { logger } from '@/modules/core/common/logging/logging';
import { useFrontendSettingsWriter } from '@/modules/settings/use-frontend-settings-writer';
import { useSetting } from '@/modules/settings/use-setting';

const NOTIFICATION_COOLDOWN_MS = 60_000;

const DAY = 86_400_000;

/**
 * How long a group has to stay quiet before it may interrupt again, indexed by how many times it
 * already has. The user sees it immediately, then a day later, then two days after that, then a
 * week after that. Past the end of the ramp it stops toasting for good.
 */
const NAG_INTERVALS: number[] = [0, DAY, 2 * DAY, 7 * DAY];

/**
 * Groups whose condition persists across logins and so is re-announced every session: a missing
 * API key is still missing tomorrow. Everything else keeps the burst cooldown alone, since a
 * multi-day schedule would silence notifications that are meant to fire once per event.
 */
const SCHEDULED_GROUPS: Set<NotificationGroup> = new Set([
  NotificationGroup.MISSING_API_KEY,
  NotificationGroup.NO_AVAILABLE_INDEXERS,
]);

/**
 * Groups whose entries are the successive steps of one flow the user just started, rather than
 * repeats of the same condition. Each step replaces the one before it, so the burst cooldown would
 * silence the outcome of an action taken seconds ago: the user would be told the browser is opening
 * and never told whether the authorization worked.
 */
const UNTHROTTLED_GROUPS: Set<NotificationGroup> = new Set([
  NotificationGroup.MONERIUM_AUTH,
]);

/** Coalescing window for schedule writes, which each persist the whole frontend settings blob. */
const FLUSH_DEBOUNCE_MS = 2000;

export interface UseNotificationCooldownReturn {
  shouldSuppress: (group: NotificationGroupKey) => boolean;
  recordDisplay: (group: NotificationGroupKey) => void;
  resetSchedule: (predicate: (group: string) => boolean) => void;
}

function isScheduled(group: NotificationGroupKey): boolean {
  const name = notificationGroupOf(group);
  return name !== undefined && SCHEDULED_GROUPS.has(name);
}

function isUnthrottled(group: NotificationGroupKey): boolean {
  const name = notificationGroupOf(group);
  return name !== undefined && UNTHROTTLED_GROUPS.has(name);
}

/** Memoises `factory`, so its dependencies are only resolved once something actually needs them. */
function createLazy<T>(factory: () => T): () => T {
  let value: T | undefined;
  return (): T => (value ??= factory());
}

/**
 * Decides whether a grouped notification may interrupt the user.
 *
 * Two layers, because they answer different questions. The burst cooldown keeps one query run
 * from toasting the same group repeatedly, and lives in session storage since it is only about
 * the current run. The nag schedule keeps a condition that outlives the session from being
 * re-announced at every login, and so persists per user.
 *
 * Shared, so that a display recorded by the store is visible to the dispatcher before the
 * debounced write lands.
 */
export const useNotificationCooldown = createSharedComposable((): UseNotificationCooldownReturn => {
  const lastDisplay: Ref<Record<string, number>> = useSessionStorage('rotki.notification.last_display', {});

  const pending = ref<Record<string, NotificationScheduleEntry>>({});

  /**
   * Resolved on first use rather than up front, so that notifications from groups with no
   * schedule never pull the settings stores into contexts that do not otherwise need them.
   *
   * ⚠️ Both of these must stay callable outside a component `setup`: a display is recorded from
   * the notification store, which is not a component. That rules out `useSettingsOperations`,
   * whose notification surface resolves `useI18n` (and would close a cycle back onto this file).
   */
  const settings = createLazy(() => ({
    schedule: useSetting('notificationSchedule'),
    updateFrontendSetting: useFrontendSettingsWriter().updateFrontendSetting,
  }));

  function entryFor(group: NotificationGroupKey): NotificationScheduleEntry | undefined {
    return get(pending)[group] ?? get(settings().schedule)[group];
  }

  /**
   * Persist the accumulated entries in one write. Several chains can exhaust their schedule
   * during the same query run, and every update rewrites the entire settings blob.
   */
  async function flush(): Promise<void> {
    const updates = get(pending);
    if (isEmpty(updates))
      return;

    set(pending, {});
    const { schedule, updateFrontendSetting } = settings();
    const status = await updateFrontendSetting({
      notificationSchedule: { ...get(schedule), ...updates },
    });

    // Losing a write only costs one extra notification later, so log it rather than raise a
    // notification about having failed to record a notification.
    if (!status.success)
      logger.warn(`Failed to persist the notification schedule: ${status.message}`);
  }

  watchDebounced(pending, () => {
    startPromise(flush());
  }, { debounce: FLUSH_DEBOUNCE_MS });

  function shouldSuppress(group: NotificationGroupKey): boolean {
    if (isUnthrottled(group))
      return false;

    const lastTime = get(lastDisplay)[group] ?? 0;
    if (Date.now() - lastTime < NOTIFICATION_COOLDOWN_MS)
      return true;

    if (!isScheduled(group))
      return false;

    const { lastShown = 0, shownCount = 0 } = entryFor(group) ?? {};
    if (shownCount >= NAG_INTERVALS.length)
      return true;

    return Date.now() - lastShown < NAG_INTERVALS[shownCount];
  }

  function recordDisplay(group: NotificationGroupKey): void {
    set(lastDisplay, {
      ...get(lastDisplay),
      [group]: Date.now(),
    });

    if (!isScheduled(group))
      return;

    const { shownCount = 0 } = entryFor(group) ?? {};
    set(pending, {
      ...get(pending),
      [group]: { lastShown: Date.now(), shownCount: shownCount + 1 },
    });
  }

  /**
   * Forget the schedule for the matching groups, so a condition the user has just acted on may
   * interrupt again if it turns out to be unresolved.
   */
  function resetSchedule(predicate: (group: string) => boolean): void {
    const { schedule, updateFrontendSetting } = settings();
    const current = get(schedule);
    const kept = Object.fromEntries(Object.entries(current).filter(([group]) => !predicate(group)));

    set(pending, Object.fromEntries(
      Object.entries(get(pending)).filter(([group]) => !predicate(group)),
    ));

    if (Object.keys(kept).length === Object.keys(current).length)
      return;

    startPromise(updateFrontendSetting({ notificationSchedule: kept }));
  }

  return { recordDisplay, resetSchedule, shouldSuppress };
});
