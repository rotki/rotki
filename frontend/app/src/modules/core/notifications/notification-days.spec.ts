import { type NotificationData, NotificationKind, Severity } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { groupByDay, NotificationDayLabel } from '@/modules/core/notifications/notification-days';

const NOW = new Date(2026, 9, 21, 15, 0);

function at(id: number, date: Date | string): NotificationData {
  return { date: typeof date === 'string' ? new Date(date) : date, display: false, duration: 0, id, kind: NotificationKind.RESULT, message: 'm', read: true, severity: Severity.INFO, title: 't' };
}

describe('modules/core/notifications/notification-days', () => {
  it('should group by local day, newest day first, keeping the order within a day', () => {
    const days = groupByDay([
      at(4, new Date(2026, 9, 21, 14, 0)),
      at(3, new Date(2026, 9, 21, 9, 0)),
      at(2, new Date(2026, 9, 20, 23, 59)),
      at(1, new Date(2026, 9, 12, 8, 0)),
    ], NOW);

    expect(days.map(day => [day.key, day.notifications.map(n => n.id)])).toEqual([
      ['2026-10-21', [4, 3]],
      ['2026-10-20', [2]],
      ['2026-10-12', [1]],
    ]);
  });

  it('should name today and yesterday, and every older day by its date', () => {
    const days = groupByDay([
      at(3, new Date(2026, 9, 21, 0, 1)),
      at(2, new Date(2026, 9, 20, 12, 0)),
      at(1, new Date(2026, 9, 19, 12, 0)),
    ], NOW);

    expect(days.map(day => day.label)).toEqual([NotificationDayLabel.TODAY, NotificationDayLabel.YESTERDAY, NotificationDayLabel.EARLIER]);
  });

  it('should read a date that arrived as a string', () => {
    const days = groupByDay([Object.assign(at(1, NOW), { date: NOW.toISOString() })], NOW);

    expect(days[0].label).toBe(NotificationDayLabel.TODAY);
  });

  it('should answer no days for no notifications', () => {
    expect(groupByDay([], NOW)).toEqual([]);
  });
});
