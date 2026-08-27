import { NotificationCategory, type NotificationData, Severity } from '@rotki/common';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';
import { useServiceKeyNotifications } from '@/modules/settings/api-keys/external/use-service-key-notifications';

function notification(overrides: Partial<NotificationData> = {}): NotificationData {
  return {
    category: NotificationCategory.DEFAULT,
    date: new Date(0),
    display: true,
    duration: 0,
    id: 1,
    message: 'message',
    severity: Severity.WARNING,
    title: 'title',
    ...overrides,
  };
}

function remaining(): number[] {
  return useNotificationsStore().prioritized.map(item => item.id);
}

describe('useServiceKeyNotifications', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  describe('dismissCategory', () => {
    it('should dismiss every notification of the category, not only the first', () => {
      useNotificationsStore().add([
        notification({ category: NotificationCategory.ETHERSCAN, id: 1 }),
        notification({ category: NotificationCategory.ETHERSCAN, id: 2 }),
      ]);

      useServiceKeyNotifications().dismissCategory(NotificationCategory.ETHERSCAN);

      expect(remaining()).toStrictEqual([]);
    });

    it('should leave the other categories alone', () => {
      useNotificationsStore().add([
        notification({ category: NotificationCategory.ETHERSCAN, id: 1 }),
        notification({ category: NotificationCategory.HELIUS, id: 2 }),
      ]);

      useServiceKeyNotifications().dismissCategory(NotificationCategory.ETHERSCAN);

      expect(remaining()).toStrictEqual([2]);
    });

    it('should read the list at call time rather than at composable creation', () => {
      const { dismissCategory } = useServiceKeyNotifications();
      useNotificationsStore().add([notification({ category: NotificationCategory.HELIUS, id: 1 })]);

      dismissCategory(NotificationCategory.HELIUS);

      expect(remaining()).toStrictEqual([]);
    });
  });

  describe('dismissNamedService', () => {
    it('should dismiss the notification whose i18n param names the service', () => {
      useNotificationsStore().add([
        notification({ i18nParam: { choice: 0, message: 'm', props: { service: 'TheGraph' } }, id: 1 }),
        notification({ i18nParam: { choice: 0, message: 'm', props: { service: 'Alchemy' } }, id: 2 }),
      ]);

      useServiceKeyNotifications().dismissNamedService('thegraph');

      expect(remaining()).toStrictEqual([2]);
    });

    it('should dismiss nothing when no notification names the service', () => {
      useNotificationsStore().add([notification({ id: 1 })]);

      useServiceKeyNotifications().dismissNamedService('thegraph');

      expect(remaining()).toStrictEqual([1]);
    });
  });
});
