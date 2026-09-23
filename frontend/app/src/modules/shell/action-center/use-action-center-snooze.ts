import type { EventHookOn } from '@vueuse/core';
import type { Ref } from 'vue';
import { startPromise } from '@shared/utils';
import { useLoggedUserIdentifier } from '@/modules/auth/use-logged-user-identifier';
import { type ActionItem, type ActionItemOption, ActionUrgency } from '@/modules/core/action-center/types';
import { HISTORY_SYNC_ROW_ID } from '@/modules/shell/action-center/row-ids';

const SNOOZE_MS = 7 * 24 * 60 * 60 * 1000;

/** How often a snooze is re-checked against its end. */
const SNOOZE_TICK_MS = 60_000;

interface Snooze {
  /** when the row counts again, in milliseconds */
  until: number;
  /** the row's count when it was snoozed; growing past it ends the snooze early */
  count: number;
}

type Snoozes = Record<string, Snooze>;

interface UseActionCenterSnoozeReturn {
  /** The row as the center shows it: set aside while snoozed, and offering a snooze when it can take one. */
  withSnooze: (item: ActionItem) => ActionItem;
  /** Fires with a row's id when it is snoozed or woken by hand, so it can read as new once it counts again. */
  onSnoozeChange: EventHookOn<string>;
}

/**
 * Whether a row can be put off for later.
 *
 * @remarks
 * Only rows that ask something of the user: what rotki retries on its own does not count toward the
 * badge anyway, a locked or already set-aside row has nothing to put off, and the history sync row
 * has a dismissal of its own.
 */
function canSnooze(item: ActionItem): boolean {
  return item.urgency !== ActionUrgency.AUTOMATIC
    && !item.locked
    && !item.informational
    && item.id !== HISTORY_SYNC_ROW_ID;
}

/** Keeps a row's lesser options ahead of the ones that silence it for good. */
function withOption(options: ActionItemOption[], option: ActionItemOption): ActionItemOption[] {
  return [...options.filter(existing => !existing.danger), option, ...options.filter(existing => existing.danger)];
}

/**
 * "Remind me later" for the action center's rows.
 *
 * @remarks
 * A snoozed row stays listed but set aside, so it stops counting toward the badge. It counts again
 * after a week, or sooner once its count grows past what it was when snoozed, since that is
 * something the user has not seen yet. Kept per user in local storage.
 */
export function useActionCenterSnooze(): UseActionCenterSnoozeReturn {
  const changed = createEventHook<string>();
  const { t } = useI18n({ useScope: 'global' });
  const userId = useLoggedUserIdentifier();
  const now = useNow({ interval: SNOOZE_TICK_MS });

  const snoozes: Ref<Snoozes> = useLocalStorage<Snoozes>(() => `${get(userId)}.rotki_action_center_snoozed`, {});

  function isSnoozed(item: ActionItem): boolean {
    const snooze = get(snoozes)[item.id];
    return snooze !== undefined && get(now).getTime() < snooze.until && item.count <= snooze.count;
  }

  function snooze(item: ActionItem): void {
    const time = Date.now();
    const current = Object.fromEntries(Object.entries(get(snoozes)).filter(([, entry]) => entry.until > time));
    set(snoozes, { ...current, [item.id]: { count: item.count, until: time + SNOOZE_MS } });
    startPromise(changed.trigger(item.id));
  }

  function wake(id: string): void {
    set(snoozes, Object.fromEntries(Object.entries(get(snoozes)).filter(([snoozedId]) => snoozedId !== id)));
    startPromise(changed.trigger(id));
  }

  function withSnooze(item: ActionItem): ActionItem {
    if (isSnoozed(item)) {
      return {
        ...item,
        informational: true,
        options: withOption(item.options, {
          icon: 'lu-bell-ring',
          id: 'remind-now',
          label: t('action_center.remind_now'),
          target: { kind: 'run', run: () => wake(item.id) },
        }),
      };
    }

    if (!canSnooze(item))
      return item;

    return {
      ...item,
      options: withOption(item.options, {
        icon: 'lu-alarm-clock',
        id: 'remind-later',
        label: t('action_center.remind_later'),
        target: { kind: 'run', run: () => snooze(item) },
      }),
    };
  }

  return { onSnoozeChange: changed.on, withSnooze };
}
