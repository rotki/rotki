import type { BackendProblem } from '@/modules/core/notifications/problems/backend-problem-tree';
import { type NotificationData, type NotificationGroup, NotificationKind } from '@rotki/common';
import { once } from 'es-toolkit';
import { useFrontendSettingsWriter } from '@/modules/settings/use-frontend-settings-writer';
import { useSetting } from '@/modules/settings/use-setting';

/** The family and location a backend problem is muted by, whatever its severity. */
export function problemMuteKey(problem: Pick<BackendProblem, 'key' | 'subject'>): string {
  return `problem:${problem.key}:${problem.subject ?? ''}`;
}

/** The group an announcement is muted by. */
export function groupMuteKey(group: NotificationGroup): string {
  return `group:${group}`;
}

/**
 * The key a notification is muted by, or nothing for one that cannot be muted.
 *
 * @remarks
 * Only a grouped announcement can be: it is the one kind that repeats under a stable identity.
 * A result, a reminder and a failure are single occurrences, and an ungrouped announcement has no
 * identity to remember.
 */
export function notificationMuteKey(notification: { kind: NotificationKind; group?: NotificationGroup }): string | undefined {
  if (notification.kind !== NotificationKind.ANNOUNCEMENT || !notification.group)
    return undefined;
  return groupMuteKey(notification.group);
}

/**
 * The last queued change to the muted list. Module scope on purpose: the dispatcher and the drawer
 * each build their own instance, and their changes have to queue behind one another.
 */
let pendingMuteWrite: Promise<void> = Promise.resolve();

interface UseNotificationMuteReturn {
  /** Whether the key is muted. */
  isMuted: (key: string | undefined) => boolean;
  /** Whether the notification belongs to a muted group. */
  isNotificationMuted: (notification: NotificationData) => boolean;
  /** Whether the backend problem's family and location are muted. */
  isProblemMuted: (problem: BackendProblem) => boolean;
  mute: (key: string) => Promise<void>;
  unmute: (key: string) => Promise<void>;
}

/**
 * Per-group mute: a muted group still lands in the drawer, under its muted section, but never pops
 * and never lights the unread dot.
 *
 * @remarks
 * An account-wide frontend setting, so a mute follows the user between logins and machines.
 * Global silent mode stays its own switch. The settings stores are resolved on first read, as
 * {@link useSilentNotifications} explains: the dispatcher builds this wherever notifications are
 * used, including contexts that never set up a pinia.
 */
export function useNotificationMute(): UseNotificationMuteReturn {
  const settings = once(() => ({
    muted: useSetting('mutedNotificationGroups'),
    updateFrontendSetting: useFrontendSettingsWriter().updateFrontendSetting,
  }));

  function isMuted(key: string | undefined): boolean {
    return key !== undefined && get(settings().muted).includes(key);
  }

  /**
   * Writes the muted list `change` derives from the current one, after every earlier change.
   *
   * @remarks
   * The setting only updates once its write lands, so a change derived before that would rebuild
   * the list without an earlier change still in flight and undo it.
   */
  async function writeMuted(change: (current: readonly string[]) => readonly string[] | undefined): Promise<void> {
    const queued = pendingMuteWrite.then(async () => {
      const next = change(get(settings().muted));
      if (next)
        await settings().updateFrontendSetting({ mutedNotificationGroups: [...next] });
    });
    pendingMuteWrite = queued.catch(() => undefined);
    await queued;
  }

  async function mute(key: string): Promise<void> {
    await writeMuted(current => current.includes(key) ? undefined : [...current, key]);
  }

  async function unmute(key: string): Promise<void> {
    await writeMuted(current => current.includes(key) ? current.filter(item => item !== key) : undefined);
  }

  return {
    isMuted,
    isNotificationMuted: notification => isMuted(notificationMuteKey(notification)),
    isProblemMuted: problem => isMuted(problemMuteKey(problem)),
    mute,
    unmute,
  };
}
