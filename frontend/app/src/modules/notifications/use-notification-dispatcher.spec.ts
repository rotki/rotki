import { NotificationCategory, NotificationGroup, type NotificationPayload, Priority, Severity } from '@rotki/common';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useNotificationsStore } from '@/modules/notifications/use-notifications-store';
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

    notify({ message: 'message-1', title: 'title-1' });

    expect(get(data)).toHaveLength(1);
    expect(get(data)[0]).toMatchObject({ message: 'message-1', title: 'title-1' });
  });

  it('should handle group notifications with cooldown', () => {
    const { notify } = useNotificationDispatcher();
    const store = useNotificationsStore();
    const { data } = storeToRefs(store);

    notify({
      display: true,
      group: NotificationGroup.NEW_DETECTED_TOKENS,
      message: 'message-1',
      title: 'title-1',
    });

    expect(get(data)[0]).toMatchObject({ display: true, group: NotificationGroup.NEW_DETECTED_TOKENS });
    const originalDate = get(data)[0].date;

    // Second notification within cooldown should suppress display
    notify({
      display: true,
      group: NotificationGroup.NEW_DETECTED_TOKENS,
      groupCount: 2,
      message: 'message-2',
      title: 'title-1',
    });

    expect(get(data)).toHaveLength(1);
    expect(get(data)[0]).toMatchObject({
      date: originalDate,
      display: false,
      groupCount: 2,
      message: 'message-2',
    });

    // After cooldown, display should be allowed again
    vi.advanceTimersByTime(NOTIFICATION_COOLDOWN_MS);

    notify({
      display: true,
      group: NotificationGroup.NEW_DETECTED_TOKENS,
      groupCount: 3,
      message: 'message-3',
      title: 'title-1',
    });

    expect(get(data)[0]).toMatchObject({ display: true, groupCount: 3, message: 'message-3' });
  });

  it('should not duplicate bulk notifications with the same message', () => {
    const { notify } = useNotificationDispatcher();
    const store = useNotificationsStore();
    const { data } = storeToRefs(store);

    const payload: NotificationPayload = {
      category: NotificationCategory.DEFAULT,
      message: 'there was a problem',
      priority: Priority.BULK,
      severity: Severity.WARNING,
      title: 'backend',
    };

    notify(payload);
    notify(payload);

    expect(get(data)).toHaveLength(1);
  });

  it('should group deserialization errors into a single notification', () => {
    const { notify } = useNotificationDispatcher();
    const store = useNotificationsStore();
    const { data } = storeToRefs(store);

    for (let i = 0; i < 10; i++) {
      notify({
        category: NotificationCategory.DEFAULT,
        message: `Could not deserialize asset ${i}`,
        priority: Priority.BULK,
        severity: Severity.WARNING,
        title: 'backend',
      });
    }

    expect(get(data)).toHaveLength(1);
    expect(get(data)[0]).toMatchObject({
      group: NotificationGroup.DESERIALIZATION_ERROR,
      groupCount: 10,
    });
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

    notify({ message: 'normal', title: 'normal' });

    notify({
      action: { action: vi.fn, label: 'Action' },
      i18nParam: { choice: 0, message: '', props: {} },
      message: 'action-msg',
      priority: Priority.ACTION,
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

    notify({ display: true, message: 'msg-1', title: 'title-1' });
    notify({ display: true, message: 'msg-2', title: 'title-2' });

    expect(get(data)).toHaveLength(2);

    store.displayed([get(data)[0].id]);
    expect(get(data)[0]).toMatchObject({ display: false });
  });
});
