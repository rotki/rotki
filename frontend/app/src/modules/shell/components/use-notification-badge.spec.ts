import { NotificationCategory, type NotificationData, Priority, Severity } from '@rotki/common';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';
import { useNotificationBadge } from '@/modules/shell/components/use-notification-badge';

function notification(overrides: Partial<NotificationData> = {}): NotificationData {
  return {
    category: NotificationCategory.DEFAULT,
    date: new Date('2026-03-04T05:06:07Z'),
    display: false,
    duration: 5000,
    id: 1,
    message: 'the message',
    read: false,
    severity: Severity.INFO,
    title: 'the title',
    ...overrides,
  };
}

describe('useNotificationBadge', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should show nothing when there is neither outstanding work nor anything new', () => {
    const store = useNotificationsStore();
    store.add([notification({ read: true })]);

    expect(useNotificationBadge().visible.value).toBe(false);
  });

  it('should show a numberless dot for something new that needs nobody', () => {
    const store = useNotificationsStore();
    store.add([notification({ priority: Priority.BULK })]);

    const { color, text, visible } = useNotificationBadge();

    expect(visible.value).toBe(true);
    expect(text.value).toBe('');
    expect(color.value).toBe('primary');
  });

  it('should count only the notifications that need the user', () => {
    const store = useNotificationsStore();
    store.add([
      notification({ id: 1, priority: Priority.ACTION }),
      notification({ id: 2, priority: Priority.BULK }),
      notification({ id: 3, priority: Priority.HIGH }),
    ]);

    expect(useNotificationBadge().text.value).toBe('1');
  });

  it('should keep counting outstanding work after the drawer has been read', () => {
    const store = useNotificationsStore();
    store.add([notification({ priority: Priority.ACTION })]);

    store.markAllRead();

    const { text, visible } = useNotificationBadge();
    expect(visible.value).toBe(true);
    expect(text.value).toBe('1');
  });

  it('should drop the dot once the drawer has been read', () => {
    const store = useNotificationsStore();
    store.add([notification({ priority: Priority.BULK })]);

    store.markAllRead();

    expect(useNotificationBadge().visible.value).toBe(false);
  });

  it('should take its colour from the worst outstanding severity, not the worst overall', () => {
    const store = useNotificationsStore();
    store.add([
      notification({ id: 1, priority: Priority.ACTION, severity: Severity.WARNING }),
      notification({ id: 2, priority: Priority.BULK, severity: Severity.ERROR }),
    ]);

    expect(useNotificationBadge().color.value).toBe('warning');
  });

  it('should escalate the colour when an outstanding item is an error', () => {
    const store = useNotificationsStore();
    store.add([
      notification({ id: 1, priority: Priority.ACTION, severity: Severity.WARNING }),
      notification({ id: 2, priority: Priority.ACTION, severity: Severity.ERROR }),
    ]);

    expect(useNotificationBadge().color.value).toBe('error');
  });

  it('should report unread separately from the count, so the dot can be named', () => {
    const store = useNotificationsStore();
    store.add([notification({ priority: Priority.BULK })]);

    const { actionCount, hasUnread } = useNotificationBadge();
    expect(hasUnread.value).toBe(true);
    expect(actionCount.value).toBe(0);

    store.markAllRead();
    expect(hasUnread.value).toBe(false);
  });

  it('should stop counting an outstanding item once its row is removed', () => {
    const store = useNotificationsStore();
    store.add([notification({ id: 7, priority: Priority.ACTION })]);

    store.remove(7);

    expect(useNotificationBadge().visible.value).toBe(false);
  });
});
