import { NotificationGroup, NotificationKind, type NotificationPayload, Severity } from '@rotki/common';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';
import { beginSession, endSession } from '@/modules/core/session/session-lifecycle';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { useNotificationDispatcher } from './use-notification-dispatcher';

/** Matches NOTIFICATION_COOLDOWN_MS in use-notification-cooldown.ts */
const NOTIFICATION_COOLDOWN_MS = 60_000;

const RESULT = NotificationKind.RESULT;

function beaconchainRateLimited(endpoint: string): NotificationPayload {
  return {
    kind: NotificationKind.FAILURE,
    message: 'Beaconcha.in is rate limited until 2025-01-15T12:00:00Z. Check logs for more details',
    severity: Severity.WARNING,
    title: endpoint,
  };
}

describe('useNotificationDispatcher', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should add a notification', () => {
    const { notify } = useNotificationDispatcher();
    const store = useNotificationsStore();
    const { data } = storeToRefs(store);

    notify({ kind: RESULT, message: 'message-1', severity: Severity.INFO, title: 'title-1' });

    expect(get(data)).toHaveLength(1);
    expect(get(data)[0]).toMatchObject({ kind: RESULT, message: 'message-1', severity: Severity.INFO, title: 'title-1' });
  });

  it('should drop a notification raised with no live session', () => {
    const { notify } = useNotificationDispatcher();
    const { data } = storeToRefs(useNotificationsStore());

    endSession();
    notify({ kind: RESULT, message: 'late failure', severity: Severity.INFO, title: 'title-1' });

    expect(get(data)).toHaveLength(0);
  });

  it('should record notifications again once the next session begins', () => {
    const { notify } = useNotificationDispatcher();
    const { data } = storeToRefs(useNotificationsStore());

    endSession();
    beginSession();
    notify({ kind: RESULT, message: 'message-1', severity: Severity.INFO, title: 'title-1' });

    expect(get(data)).toHaveLength(1);
  });

  it('should handle group notifications with cooldown', () => {
    const { notify } = useNotificationDispatcher();
    const store = useNotificationsStore();
    const { data } = storeToRefs(store);
    const kind = NotificationKind.ANNOUNCEMENT;

    notify({ group: NotificationGroup.NEW_DETECTED_TOKENS, kind, message: 'message-1', severity: Severity.INFO, title: 'title-1' });

    expect(get(data)[0]).toMatchObject({ display: true, group: NotificationGroup.NEW_DETECTED_TOKENS });
    const originalDate = get(data)[0].date;

    notify({ group: NotificationGroup.NEW_DETECTED_TOKENS, groupCount: 2, kind, message: 'message-2', severity: Severity.INFO, title: 'title-1' });

    expect(get(data)).toHaveLength(1);
    expect(get(data)[0]).toMatchObject({
      date: originalDate,
      display: false,
      groupCount: 2,
      message: 'message-2',
    });

    vi.advanceTimersByTime(NOTIFICATION_COOLDOWN_MS);

    notify({ group: NotificationGroup.NEW_DETECTED_TOKENS, groupCount: 3, kind, message: 'message-3', severity: Severity.INFO, title: 'title-1' });

    expect(get(data)[0]).toMatchObject({ display: true, groupCount: 3, message: 'message-3' });
  });

  it('should keep the date a notification says it happened, new or updating its group', () => {
    const { notify } = useNotificationDispatcher();
    const { data } = storeToRefs(useNotificationsStore());
    const earlier = new Date('2026-09-30T08:00:00Z');
    const later = new Date('2026-09-30T09:00:00Z');

    notify({ date: earlier, kind: RESULT, message: 'plain', severity: Severity.INFO, title: 'plain' });
    notify({ date: earlier, group: NotificationGroup.NEW_DETECTED_TOKENS, kind: RESULT, message: 'first', severity: Severity.INFO, title: 'grouped' });
    vi.advanceTimersByTime(NOTIFICATION_COOLDOWN_MS);
    notify({ date: later, group: NotificationGroup.NEW_DETECTED_TOKENS, groupCount: 2, kind: RESULT, message: 'second', severity: Severity.INFO, title: 'grouped' });

    expect(get(data).map(({ date, message }) => [message, date])).toEqual(expect.arrayContaining([
      ['plain', earlier],
      ['second', later],
    ]));
  });

  it('should not move a grouped row back in time for an update dated before it', () => {
    const { notify } = useNotificationDispatcher();
    const { data } = storeToRefs(useNotificationsStore());
    const recent = new Date('2026-09-30T09:00:00Z');

    notify({ date: recent, group: NotificationGroup.NEW_DETECTED_TOKENS, kind: RESULT, message: 'recent', severity: Severity.INFO, title: 'grouped' });
    vi.advanceTimersByTime(NOTIFICATION_COOLDOWN_MS);
    notify({ date: new Date('2026-09-30T07:00:00Z'), group: NotificationGroup.NEW_DETECTED_TOKENS, groupCount: 2, kind: RESULT, message: 'older', severity: Severity.INFO, title: 'grouped' });

    expect(get(data)[0].date).toEqual(recent);
  });

  it('should carry the extras of an update into its grouped row', () => {
    const { notify } = useNotificationDispatcher();
    const { data } = storeToRefs(useNotificationsStore());

    notify({ extras: { sentence: 'first' }, group: NotificationGroup.NEW_DETECTED_TOKENS, kind: RESULT, message: 'first', severity: Severity.INFO, title: 'grouped' });
    notify({ extras: { sentence: 'second' }, group: NotificationGroup.NEW_DETECTED_TOKENS, groupCount: 2, kind: RESULT, message: 'second', severity: Severity.INFO, title: 'grouped' });

    expect(get(data)[0].extras).toEqual({ sentence: 'second' });
  });

  it('should group beaconchain rate limit notifications and list endpoints', () => {
    const { notify } = useNotificationDispatcher();
    const store = useNotificationsStore();
    const { data } = storeToRefs(store);

    notify(beaconchainRateLimited('Endpoint 1'));
    notify(beaconchainRateLimited('Endpoint 2'));
    notify(beaconchainRateLimited('Endpoint 3'));

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

    notify(beaconchainRateLimited('Endpoint 1'));
    notify(beaconchainRateLimited('Endpoint 1'));
    notify(beaconchainRateLimited('Endpoint 2'));
    notify(beaconchainRateLimited('Endpoint 1'));

    expect(get(data)).toHaveLength(1);
    expect(get(data)[0]).toMatchObject({
      extras: { endpoints: ['Endpoint 1', 'Endpoint 2'], until: '2025-01-15T12:00:00Z' },
      groupCount: 2,
    });
  });

  it('should list the newest notification first, whatever its kind', () => {
    const { notify } = useNotificationDispatcher();
    const { newestFirst } = storeToRefs(useNotificationsStore());

    notify({ kind: NotificationKind.ANNOUNCEMENT, message: 'older', severity: Severity.INFO, title: 'older' });
    vi.advanceTimersByTime(1_000);
    notify({ kind: NotificationKind.FAILURE, message: 'newer', severity: Severity.INFO, title: 'newer' });

    expect(get(newestFirst).map(({ message }) => message)).toEqual(['newer', 'older']);
  });

  it('should not keep more than 200 notifications', () => {
    const { notify } = useNotificationDispatcher();
    const store = useNotificationsStore();
    const { data } = storeToRefs(store);

    for (let i = 0; i < 205; i++) {
      notify({
        kind: NotificationKind.FAILURE,
        message: `Warning number ${i + 1}`,
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

    notify({ kind: RESULT, message: 'msg-1', severity: Severity.INFO, title: 'title-1' });
    notify({ kind: RESULT, message: 'msg-2', severity: Severity.INFO, title: 'title-2' });

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

      notify({ kind: RESULT, message: 'msg', severity: Severity.INFO, title: 'title' });

      expect(get(queue)).toHaveLength(0);
      expect(get(data)[0]).toMatchObject({ display: false, message: 'msg' });
    });

    it('should still deliver the notification to the notification area', () => {
      silence();
      const { notify } = useNotificationDispatcher();
      const { data } = storeToRefs(useNotificationsStore());

      notify({
        action: { action: vi.fn(), label: 'Configure' },
        kind: NotificationKind.ANNOUNCEMENT,
        message: 'msg',
        severity: Severity.INFO,
        title: 'title',
      });

      // Silenced, not suppressed: the row and its action have to survive.
      expect(get(data)).toHaveLength(1);
      expect(get(data)[0].action).toBeDefined();
      expect(get(data)[0].kind).toBe(NotificationKind.ANNOUNCEMENT);
    });

    it('should still collapse grouped notifications while silent', () => {
      silence();
      const { notify } = useNotificationDispatcher();
      const { data } = storeToRefs(useNotificationsStore());

      notify({ group: NotificationGroup.NEW_DETECTED_TOKENS, kind: RESULT, message: 'first', severity: Severity.INFO, title: 'title' });
      notify({ group: NotificationGroup.NEW_DETECTED_TOKENS, groupCount: 2, kind: RESULT, message: 'second', severity: Severity.INFO, title: 'title' });

      expect(get(data)).toHaveLength(1);
      expect(get(data)[0]).toMatchObject({ display: false, groupCount: 2, message: 'second' });
    });

    it('should let notifications interrupt again once it is turned off', () => {
      silence();
      const { notify } = useNotificationDispatcher();
      const { queue } = storeToRefs(useNotificationsStore());

      notify({ kind: RESULT, message: 'quiet', severity: Severity.INFO, title: 'title' });
      unsilence();
      notify({ kind: RESULT, message: 'loud', severity: Severity.INFO, title: 'title' });

      expect(get(queue)).toHaveLength(1);
      expect(get(queue)[0]).toMatchObject({ message: 'loud' });
    });
  });
});
