import { NotificationCategory, type NotificationData, type NotificationPayload, Priority, Severity } from '@rotki/common';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createNotification } from '@/modules/core/notifications/notification-utils';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';

function testPayload(overrides: Partial<NotificationPayload> & { message: string; title: string }): NotificationPayload {
  return {
    category: NotificationCategory.DEFAULT,
    severity: Severity.INFO,
    ...overrides,
  };
}

describe('useNotificationsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should add and remove notifications', () => {
    const store = useNotificationsStore();
    const { data } = storeToRefs(store);

    store.add([createNotification(store.getNextId(), testPayload({
      message: 'message-1',
      title: 'title-1',
    }))]);

    expect(get(data)).toHaveLength(1);
    expect(get(data)[0]).toMatchObject({ message: 'message-1', title: 'title-1' });

    store.remove(get(data)[0].id);
    expect(get(data)).toHaveLength(0);
  });

  it('should replace all notifications', () => {
    const store = useNotificationsStore();
    const { data } = storeToRefs(store);

    store.add([
      createNotification(store.getNextId(), testPayload({ message: 'msg-1', title: 'title-1' })),
      createNotification(store.getNextId(), testPayload({ message: 'msg-2', title: 'title-2' })),
    ]);

    expect(get(data)).toHaveLength(2);

    store.replace([createNotification(99, testPayload({ message: 'replaced', title: 'replaced' }))]);
    expect(get(data)).toHaveLength(1);
    expect(get(data)[0]).toMatchObject({ message: 'replaced' });
  });

  it('should remove matching notification', () => {
    const store = useNotificationsStore();
    const { data } = storeToRefs(store);

    store.add([
      createNotification(store.getNextId(), testPayload({ message: 'keep-me', title: 'keep' })),
      createNotification(store.getNextId(), testPayload({ message: 'remove-me', title: 'remove' })),
    ]);

    store.removeMatching(n => n.message === 'remove-me');
    expect(get(data)).toHaveLength(1);
    expect(get(data)[0]).toMatchObject({ message: 'keep-me' });
  });

  it('should sort prioritized by priority desc then date desc', () => {
    const store = useNotificationsStore();
    const { prioritized } = storeToRefs(store);

    store.add([
      createNotification(store.getNextId(), testPayload({ message: 'normal', priority: Priority.NORMAL, title: 'normal' })),
    ]);

    vi.advanceTimersByTime(1000);

    store.add([
      createNotification(store.getNextId(), testPayload({ message: 'action', priority: Priority.ACTION, title: 'action' })),
    ]);

    expect(get(prioritized)[0]).toMatchObject({ message: 'action' });
    expect(get(prioritized)[1]).toMatchObject({ message: 'normal' });
  });

  it('should cap at 200 notifications', () => {
    const store = useNotificationsStore();
    const { data, messageOverflow } = storeToRefs(store);

    const batch: NotificationData[] = [];
    for (let i = 0; i < 205; i++) {
      vi.advanceTimersByTime(100);
      batch.push(createNotification(store.getNextId(), testPayload({
        message: `msg-${i}`,
        priority: Priority.BULK,
        title: 'bulk',
      })));
    }

    store.add(batch);
    expect(get(data)).toHaveLength(200);

    // trimmedCopy returns 199 items (room for one new entry) and sets overflow
    const copy = store.trimmedCopy();
    expect(copy).toHaveLength(199);
    expect(get(messageOverflow)).toBe(true);
  });

  it('should filter queue for displayed notifications', () => {
    const store = useNotificationsStore();
    const { queue } = storeToRefs(store);

    store.add([
      createNotification(store.getNextId(), testPayload({ display: true, message: 'shown', title: 'shown' })),
      createNotification(store.getNextId(), testPayload({ message: 'hidden', title: 'hidden' })),
    ]);

    expect(get(queue)).toHaveLength(1);
    expect(get(queue)[0]).toMatchObject({ message: 'shown' });
  });

  it('should mark notifications as displayed', () => {
    const store = useNotificationsStore();
    const { data } = storeToRefs(store);

    store.add([
      createNotification(store.getNextId(), testPayload({ display: true, message: 'msg', title: 'title' })),
    ]);

    const id = get(data)[0].id;
    store.displayed([id]);

    expect(get(data)[0].display).toBe(false);
  });
});
