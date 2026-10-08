import { NotificationCategory, NotificationGroup, type NotificationPayload, Priority, Severity } from '@rotki/common';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';
import { beginSession, endSession } from '@/modules/core/session/session-lifecycle';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { useNotificationDispatcher } from './use-notification-dispatcher';

/** Matches NOTIFICATION_COOLDOWN_MS in use-notification-cooldown.ts */
const NOTIFICATION_COOLDOWN_MS = 60_000;

describe('useNotificationDispatcher', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should add a normal notification', () => {
    const { notify } = useNotificationDispatcher();
    const store = useNotificationsStore();
    const { data } = storeToRefs(store);

    notify({ message: 'message-1', severity: Severity.INFO, title: 'title-1' });

    expect(get(data)).toHaveLength(1);
    expect(get(data)[0]).toMatchObject({ message: 'message-1', severity: Severity.INFO, title: 'title-1' });
  });

  it('should drop a notification raised with no live session', () => {
    const { notify } = useNotificationDispatcher();
    const { data } = storeToRefs(useNotificationsStore());

    endSession();
    notify({ message: 'late failure', severity: Severity.INFO, title: 'title-1' });

    expect(get(data)).toHaveLength(0);
  });

  it('should record notifications again once the next session begins', () => {
    const { notify } = useNotificationDispatcher();
    const { data } = storeToRefs(useNotificationsStore());

    endSession();
    beginSession();
    notify({ message: 'message-1', severity: Severity.INFO, title: 'title-1' });

    expect(get(data)).toHaveLength(1);
  });

  it('should handle group notifications with cooldown', () => {
    const { notify } = useNotificationDispatcher();
    const store = useNotificationsStore();
    const { data } = storeToRefs(store);

    notify({ group: NotificationGroup.NEW_DETECTED_TOKENS, message: 'message-1', priority: Priority.ACTION, severity: Severity.INFO, title: 'title-1' });

    expect(get(data)[0]).toMatchObject({ display: true, group: NotificationGroup.NEW_DETECTED_TOKENS });
    const originalDate = get(data)[0].date;

    // Second notification within cooldown should suppress display
    notify({ group: NotificationGroup.NEW_DETECTED_TOKENS, groupCount: 2, message: 'message-2', priority: Priority.ACTION, severity: Severity.INFO, title: 'title-1' });

    expect(get(data)).toHaveLength(1);
    expect(get(data)[0]).toMatchObject({
      date: originalDate,
      display: false,
      groupCount: 2,
      message: 'message-2',
    });

    vi.advanceTimersByTime(NOTIFICATION_COOLDOWN_MS);

    notify({ group: NotificationGroup.NEW_DETECTED_TOKENS, groupCount: 3, message: 'message-3', priority: Priority.ACTION, severity: Severity.INFO, title: 'title-1' });

    expect(get(data)[0]).toMatchObject({ display: true, groupCount: 3, message: 'message-3' });
  });

  it('should keep the date a notification says it happened, new or updating its group', () => {
    const { notify } = useNotificationDispatcher();
    const { data } = storeToRefs(useNotificationsStore());
    const earlier = new Date('2026-09-30T08:00:00Z');
    const later = new Date('2026-09-30T09:00:00Z');

    notify({ date: earlier, message: 'plain', severity: Severity.INFO, title: 'plain' });
    notify({ date: earlier, group: NotificationGroup.NEW_DETECTED_TOKENS, message: 'first', severity: Severity.INFO, title: 'grouped' });
    vi.advanceTimersByTime(NOTIFICATION_COOLDOWN_MS);
    notify({ date: later, group: NotificationGroup.NEW_DETECTED_TOKENS, groupCount: 2, message: 'second', severity: Severity.INFO, title: 'grouped' });

    expect(get(data).map(({ date, message }) => [message, date])).toEqual(expect.arrayContaining([
      ['plain', earlier],
      ['second', later],
    ]));
  });

  it('should not move a grouped row back in time for an update dated before it', () => {
    const { notify } = useNotificationDispatcher();
    const { data } = storeToRefs(useNotificationsStore());
    const recent = new Date('2026-09-30T09:00:00Z');

    notify({ date: recent, group: NotificationGroup.NEW_DETECTED_TOKENS, message: 'recent', severity: Severity.INFO, title: 'grouped' });
    vi.advanceTimersByTime(NOTIFICATION_COOLDOWN_MS);
    notify({ date: new Date('2026-09-30T07:00:00Z'), group: NotificationGroup.NEW_DETECTED_TOKENS, groupCount: 2, message: 'older', severity: Severity.INFO, title: 'grouped' });

    expect(get(data)[0].date).toEqual(recent);
  });

  it('should carry the extras of an update into its grouped row', () => {
    const { notify } = useNotificationDispatcher();
    const { data } = storeToRefs(useNotificationsStore());

    notify({ extras: { sentence: 'first' }, group: NotificationGroup.NEW_DETECTED_TOKENS, message: 'first', severity: Severity.INFO, title: 'grouped' });
    notify({ extras: { sentence: 'second' }, group: NotificationGroup.NEW_DETECTED_TOKENS, groupCount: 2, message: 'second', severity: Severity.INFO, title: 'grouped' });

    expect(get(data)[0].extras).toEqual({ sentence: 'second' });
  });

  it('should group beaconchain rate limit notifications and list endpoints', () => {
    const { notify } = useNotificationDispatcher();
    const store = useNotificationsStore();
    const { data } = storeToRefs(store);

    const getMessage = (endpoint: string): NotificationPayload => ({
      category: NotificationCategory.DEFAULT,
      message: 'Beaconcha.in is rate limited until 2025-01-15T12:00:00Z. Check logs for more details',
      severity: Severity.WARNING,
      title: endpoint,
    });

    notify(getMessage('Endpoint 1'));
    notify(getMessage('Endpoint 2'));
    notify(getMessage('Endpoint 3'));

    expect(get(data)).toHaveLength(1);
    expect(get(data)[0]).toMatchObject({
      extras: { endpoints: ['Endpoint 1', 'Endpoint 2', 'Endpoint 3'], until: '2025-01-15T12:00:00Z' },
      group: NotificationGroup.BEACONCHAIN_RATE_LIMITED,
      groupCount: 3,
    });
  });

  it('should not add duplicate endpoints to beaconchain rate limit notification', () => {
    const { notify } = useNotificationDispatcher();
    const store = useNotificationsStore();
    const { data } = storeToRefs(store);

    const getMessage = (endpoint: string): NotificationPayload => ({
      category: NotificationCategory.DEFAULT,
      message: 'Beaconcha.in is rate limited until 2025-01-15T12:00:00Z. Check logs for more details',
      severity: Severity.WARNING,
      title: endpoint,
    });

    notify(getMessage('Endpoint 1'));
    notify(getMessage('Endpoint 1'));
    notify(getMessage('Endpoint 2'));
    notify(getMessage('Endpoint 1'));

    expect(get(data)).toHaveLength(1);
    expect(get(data)[0]).toMatchObject({
      extras: { endpoints: ['Endpoint 1', 'Endpoint 2'], until: '2025-01-15T12:00:00Z' },
      groupCount: 2,
    });
  });

  it('should keep action notifications on top via store prioritized', () => {
    const { notify } = useNotificationDispatcher();
    const store = useNotificationsStore();
    const { prioritized } = storeToRefs(store);

    notify({ message: 'normal', severity: Severity.INFO, title: 'normal' });

    notify({
      action: { action: vi.fn, label: 'Action' },
      message: 'action-msg',
      priority: Priority.ACTION,
      severity: Severity.INFO,
      title: 'action',
    });

    expect(get(prioritized)[0]).toMatchObject({ message: 'action-msg' });
    expect(get(prioritized)[1]).toMatchObject({ message: 'normal' });
  });

  it('should not keep more than 200 notifications', () => {
    const { notify } = useNotificationDispatcher();
    const store = useNotificationsStore();
    const { data } = storeToRefs(store);

    for (let i = 0; i < 205; i++) {
      notify({
        category: NotificationCategory.DEFAULT,
        message: `Warning number ${i + 1}`,
        priority: Priority.BULK,
        severity: Severity.WARNING,
        title: 'backend',
      });
      vi.advanceTimersByTime(1_000);
    }

    expect(get(data).length).toBeLessThanOrEqual(200);
  });

  it('should track displayed state via store', () => {
    const { notify } = useNotificationDispatcher();
    const store = useNotificationsStore();
    const { data } = storeToRefs(store);

    notify({ message: 'msg-1', severity: Severity.INFO, title: 'title-1' });
    notify({ message: 'msg-2', severity: Severity.INFO, title: 'title-2' });

    expect(get(data)).toHaveLength(2);

    store.displayed([get(data)[0].id]);
    expect(get(data)[0]).toMatchObject({ display: false });
  });

  describe('silent mode', () => {
    function silence(): void {
      useSettingsRepo().updateFrontend({ silentNotifications: true });
    }

    function unsilence(): void {
      useSettingsRepo().updateFrontend({ silentNotifications: false });
    }

    it('should keep a notification out of the popup queue', () => {
      silence();
      const { notify } = useNotificationDispatcher();
      const { data, queue } = storeToRefs(useNotificationsStore());

      notify({ message: 'msg', severity: Severity.INFO, title: 'title' });

      expect(get(queue)).toHaveLength(0);
      expect(get(data)[0]).toMatchObject({ display: false, message: 'msg' });
    });

    it('should still deliver the notification to the notification area', () => {
      silence();
      const { notify } = useNotificationDispatcher();
      const { data } = storeToRefs(useNotificationsStore());

      notify({
        action: { action: vi.fn(), label: 'Configure' },
        message: 'msg',
        priority: Priority.ACTION,
        severity: Severity.INFO,
        title: 'title',
      });

      // Silenced, not suppressed: the row and its action have to survive.
      expect(get(data)).toHaveLength(1);
      expect(get(data)[0].action).toBeDefined();
      expect(get(data)[0].priority).toBe(Priority.ACTION);
    });

    it('should still collapse grouped notifications while silent', () => {
      silence();
      const { notify } = useNotificationDispatcher();
      const { data } = storeToRefs(useNotificationsStore());

      notify({ group: NotificationGroup.NEW_DETECTED_TOKENS, message: 'first', severity: Severity.INFO, title: 'title' });
      notify({ group: NotificationGroup.NEW_DETECTED_TOKENS, groupCount: 2, message: 'second', severity: Severity.INFO, title: 'title' });

      expect(get(data)).toHaveLength(1);
      expect(get(data)[0]).toMatchObject({ display: false, groupCount: 2, message: 'second' });
    });

    it('should let notifications interrupt again once it is turned off', () => {
      silence();
      const { notify } = useNotificationDispatcher();
      const { queue } = storeToRefs(useNotificationsStore());

      notify({ message: 'quiet', priority: Priority.HIGH, severity: Severity.INFO, title: 'title' });
      unsilence();
      notify({ message: 'loud', priority: Priority.HIGH, severity: Severity.INFO, title: 'title' });

      expect(get(queue)).toHaveLength(1);
      expect(get(queue)[0]).toMatchObject({ message: 'loud' });
    });
  });
});
