import type { NotificationData } from '@rotki/common';

export const NotificationDayLabel = {
  EARLIER: 'earlier',
  TODAY: 'today',
  YESTERDAY: 'yesterday',
} as const;

export type NotificationDayLabel = (typeof NotificationDayLabel)[keyof typeof NotificationDayLabel];

/** One calendar day of the drawer's history. */
export interface NotificationDay {
  /** The day in local time, `YYYY-MM-DD`, unique within the history. */
  readonly key: string;
  /** Midnight at the start of the day, local time. */
  readonly date: Date;
  /** How the drawer names the day: today, yesterday, or by its date. */
  readonly label: NotificationDayLabel;
  /** In the order they were given, newest first. */
  readonly notifications: readonly NotificationData[];
}

export function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function dayKey(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${date.getFullYear()}-${month}-${day}`;
}

function labelOf(day: Date, today: Date): NotificationDayLabel {
  const yesterday = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1);
  if (day.getTime() === today.getTime())
    return NotificationDayLabel.TODAY;
  if (day.getTime() === yesterday.getTime())
    return NotificationDayLabel.YESTERDAY;
  return NotificationDayLabel.EARLIER;
}

/**
 * Groups notifications by the local calendar day they arrived on, newest day first.
 *
 * @remarks
 * A notification's date is rebuilt through `new Date`, since one that crossed a serialization
 * boundary carries it as a string.
 *
 * @param notifications - newest first, as the store keeps them
 * @param now - when "today" is, the current time unless a caller pins it
 */
export function groupByDay(notifications: readonly NotificationData[], now: Date = new Date()): NotificationDay[] {
  const today = startOfDay(now);
  const days = new Map<string, { date: Date; notifications: NotificationData[] }>();

  for (const notification of notifications) {
    const date = startOfDay(new Date(notification.date));
    const key = dayKey(date);
    const day = days.get(key);
    if (day)
      day.notifications.push(notification);
    else
      days.set(key, { date, notifications: [notification] });
  }

  return Array.from(days.entries(), ([key, day]) => ({ ...day, key, label: labelOf(day.date, today) }))
    .sort((a, b) => b.date.getTime() - a.date.getTime());
}
