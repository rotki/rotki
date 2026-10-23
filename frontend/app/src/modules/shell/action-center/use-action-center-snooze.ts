import type { EventHookOn } from '@vueuse/core';
import type { Ref } from 'vue';
import type { ActionItem, ActionItemOption } from '@/modules/core/action-center/types';
import { startPromise } from '@shared/utils';
import { useLoggedUserIdentifier } from '@/modules/auth/use-logged-user-identifier';
import { HISTORY_SYNC_ROW_ID } from '@/modules/shell/action-center/row-ids';

const SNOOZE_MS = 7 * 24 * 60 * 60 * 1000;

/** How often a snooze is re-checked against its end. */
const SNOOZE_TICK_MS = 60_000;

/** Why a row the user put away is set aside: for a while, or until they unmute it. */
export const SetAside = {
  MUTED: 'muted',
  SNOOZED: 'snoozed',
} as const;

export type SetAside = (typeof SetAside)[keyof typeof SetAside];

interface Snooze {
  /** when the row counts again, in milliseconds */
  until: number;
  /** the row's count when it was snoozed; growing past it ends the snooze early */
  count: number;
}

type Snoozes = Record<string, Snooze>;

/** A row the user snoozed, muted, or brought back by hand. */
export interface SetAsideChange {
  id: string;
  /** how the row was set aside just before the change; undefined when it was not */
  from: SetAside | undefined;
}

interface UseActionCenterSnoozeReturn {
  /** The row as the center shows it: set aside while snoozed or muted, and offering whichever of the two it can take. */
  withSnooze: (item: ActionItem) => ActionItem;
  /** How the user put the row away, given the row as its source raised it; undefined when they did not. */
  setAsideOf: (item: ActionItem) => SetAside | undefined;
  /** Fires on every change by hand, so the row can read as new once it counts again and keep its place while the center is open. */
  onSnoozeChange: EventHookOn<SetAsideChange>;
}

/**
 * Whether a row can be put off for later.
 *
 * @remarks
 * Any row that counts toward the badge, including what rotki retries on its own: a locked or already
 * set-aside row has nothing to put off, and the history sync row has a dismissal of its own.
 */
function canSnooze(item: ActionItem): boolean {
  return !item.locked
    && !item.informational
    && item.id !== HISTORY_SYNC_ROW_ID;
}

/** Whether a row can be muted: any row that can be snoozed, unless it already offers a way to silence it for good. */
function canMute(item: ActionItem): boolean {
  return canSnooze(item) && !item.options.some(option => option.danger);
}

/** Keeps a row's lesser options ahead of the ones that silence it for good. */
function withOptions(options: ActionItemOption[], added: ActionItemOption[]): ActionItemOption[] {
  return [...options.filter(existing => !existing.danger), ...added, ...options.filter(existing => existing.danger)];
}

/**
 * "Remind me later" and "Mute" for the action center's rows.
 *
 * @remarks
 * A snoozed or muted row stops counting toward the badge, says so on its status line, and the
 * center keeps it out of the list until the user asks to see it. A snoozed row counts again after a week, or sooner once its count
 * grows past what it was when snoozed, since that is something the user has not seen yet. A muted
 * row stays put away until the user unmutes it. Both are kept per user in local storage.
 */
export function useActionCenterSnooze(): UseActionCenterSnoozeReturn {
  const changed = createEventHook<SetAsideChange>();
  const { locale, t } = useI18n({ useScope: 'global' });
  const userId = useLoggedUserIdentifier();
  const now = useNow({ scheduler: tick => useIntervalFn(tick, SNOOZE_TICK_MS) });

  const snoozes: Ref<Snoozes> = useLocalStorage<Snoozes>(() => `${get(userId)}.rotki_action_center_snoozed`, {});
  const muted: Ref<string[]> = useLocalStorage<string[]>(() => `${get(userId)}.rotki_action_center_muted`, []);

  function isSnoozed(item: ActionItem): boolean {
    const snooze = get(snoozes)[item.id];
    return snooze !== undefined && get(now).getTime() < snooze.until && item.count <= snooze.count;
  }

  function setAsideOf(item: ActionItem): SetAside | undefined {
    if (get(muted).includes(item.id))
      return SetAside.MUTED;
    return isSnoozed(item) ? SetAside.SNOOZED : undefined;
  }

  function withoutSnooze(id: string): Snoozes {
    const time = Date.now();
    return Object.fromEntries(Object.entries(get(snoozes)).filter(([snoozedId, entry]) => snoozedId !== id && entry.until > time));
  }

  /** Applies a change to the row and reports it, with how the row was set aside beforehand. */
  function change(item: ActionItem, apply: (id: string) => void): void {
    const from = setAsideOf(item);
    apply(item.id);
    startPromise(changed.trigger({ from, id: item.id }));
  }

  function snooze(item: ActionItem): void {
    change(item, id => set(snoozes, { ...withoutSnooze(id), [id]: { count: item.count, until: Date.now() + SNOOZE_MS } }));
  }

  function wake(item: ActionItem): void {
    change(item, id => set(snoozes, withoutSnooze(id)));
  }

  function mute(item: ActionItem): void {
    change(item, (id) => {
      set(snoozes, withoutSnooze(id));
      set(muted, [...get(muted).filter(mutedId => mutedId !== id), id]);
    });
  }

  function unmute(item: ActionItem): void {
    change(item, id => set(muted, get(muted).filter(mutedId => mutedId !== id)));
  }

  function muteOption(item: ActionItem): ActionItemOption {
    return {
      icon: 'lu-bell-off',
      id: 'mute',
      label: t('action_center.mute'),
      target: { kind: 'run', run: () => mute(item) },
    };
  }

  function snoozedUntil(id: string): string {
    const until = new Date(get(snoozes)[id]?.until ?? Date.now());
    return t('action_center.set_aside.snoozed_until', { date: until.toLocaleDateString(get(locale) || undefined, { day: 'numeric', month: 'short' }) });
  }

  function withSnooze(item: ActionItem): ActionItem {
    const setAside = setAsideOf(item);

    if (setAside === SetAside.MUTED) {
      return {
        ...item,
        informational: true,
        status: t('action_center.set_aside.muted'),
        options: withOptions(item.options, [{
          icon: 'lu-bell',
          id: 'unmute',
          label: t('action_center.unmute'),
          target: { kind: 'run', run: () => unmute(item) },
        }]),
      };
    }

    if (setAside === SetAside.SNOOZED) {
      return {
        ...item,
        informational: true,
        status: snoozedUntil(item.id),
        options: withOptions(item.options, [{
          icon: 'lu-bell-ring',
          id: 'remind-now',
          label: t('action_center.remind_now'),
          target: { kind: 'run', run: () => wake(item) },
        }, ...(canMute(item) ? [muteOption(item)] : [])]),
      };
    }

    if (!canSnooze(item))
      return item;

    return {
      ...item,
      options: withOptions(item.options, [{
        icon: 'lu-alarm-clock',
        id: 'remind-later',
        label: t('action_center.remind_later'),
        target: { kind: 'run', run: () => snooze(item) },
      }, ...(canMute(item) ? [muteOption(item)] : [])]),
    };
  }

  return { onSnoozeChange: changed.on, setAsideOf, withSnooze };
}
