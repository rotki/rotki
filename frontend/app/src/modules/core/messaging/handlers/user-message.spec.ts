import type { MessageDelivery } from '@/modules/core/messaging/interfaces';
import type { UserMessageData } from '@/modules/core/messaging/types/base';
import { assert, type Notification, NotificationCategory, Priority, Severity } from '@rotki/common';
import { mockT } from '@test/i18n';
import { createCustomPinia } from '@test/utils/create-pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { createUserMessageHandler } from '@/modules/core/messaging/handlers/user-message';
import { userMessageGroup } from '@/modules/core/messaging/user-message-group';
import { createNotification } from '@/modules/core/notifications/notification-utils';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';
import {
  PremiumInactiveCause,
  RaisedConditionKind,
  useRaisedConditionsStore,
} from '@/modules/shell/action-center/use-raised-conditions-store';

vi.mock('@/modules/core/common/use-locations', () => ({
  useLocations: (): { getLocationData: (id: string) => { name: string } | undefined } => ({
    getLocationData: (id: string) => (id === 'kucoin' ? { name: 'KuCoin' } : undefined),
  }),
}));

const badData: UserMessageData = {
  fields: { error: 'Missing key: amount', record: 'balance' },
  group: ['error', 'bad_data', 'kucoin', 'balance'],
  key: 'bad_data',
  subject: 'kucoin',
  value: 'Failed to deserialize a kucoin balance. Ignoring it.',
  verbosity: 'error',
};

const localDb: UserMessageData = {
  fields: { entry: 'tag' },
  group: ['warning', 'local_db', null, 'tag'],
  key: 'local_db',
  subject: null,
  value: 'Could not read a tag',
  verbosity: 'warning',
};

function authFailure(service: string, account: string | null): UserMessageData {
  return {
    fields: { account, service },
    group: ['error', 'auth', null, service, account],
    key: 'auth',
    subject: null,
    value: `${service} rejected the key`,
    verbosity: 'error',
  };
}

describe('createUserMessageHandler', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    useLocationStore().$patch({ allLocations: { binance: { isExchange: true } } });
  });

  async function notificationFor(message: UserMessageData, delivery?: MessageDelivery, handler = createUserMessageHandler(mockT)): Promise<Notification> {
    const result = await handler.handle(message, delivery);
    assert(result);
    return result;
  }

  it('should show the sentence of a first occurrence under a title naming its family and location', async () => {
    const result = await notificationFor(badData);

    expect(result).toMatchObject({
      category: NotificationCategory.DEFAULT,
      group: userMessageGroup(badData),
      groupCount: 1,
      message: badData.value,
      severity: Severity.ERROR,
      title: 'notification_messages.user_message.with_subject::KuCoin, notification_messages.user_message.title.bad_data',
    });
  });

  it('should title a message about no location by its family alone', async () => {
    const result = await notificationFor(localDb);

    expect(result).toMatchObject({
      severity: Severity.WARNING,
      title: 'notification_messages.user_message.title.local_db',
    });
  });

  it('should add every send the backend held to the count of the row it folds into', async () => {
    const { data } = storeToRefs(useNotificationsStore());
    set(data, [createNotification(1, { group: userMessageGroup(badData), groupCount: 2, message: 'earlier', severity: Severity.ERROR, title: 'kucoin' })]);

    const result = await notificationFor(badData, { count: 3 });

    expect(result).toMatchObject({
      groupCount: 5,
      message: `notification_messages.repeated::5, ${badData.value}`,
    });
  });

  it('should keep the newer sentence when a held repeat is older than the row', async () => {
    const rowDate = new Date('2026-09-30T09:00:00Z');
    const { data } = storeToRefs(useNotificationsStore());
    set(data, [{
      ...createNotification(1, { extras: { sentence: 'newer' }, group: userMessageGroup(badData), groupCount: 1, message: 'newer', severity: Severity.ERROR, title: 'kucoin' }),
      date: rowDate,
    }]);
    const handler = createUserMessageHandler(mockT);

    const older = await notificationFor(badData, { count: 1, lastSent: new Date('2026-09-30T07:00:00Z') }, handler);
    const newer = await notificationFor(badData, { count: 1, lastSent: new Date('2026-09-30T10:00:00Z') }, handler);

    expect(older.message).toBe('notification_messages.repeated::2, newer');
    expect(newer.message).toBe(`notification_messages.repeated::2, ${badData.value}`);
  });

  it.each([badData, localDb])('should keep a $key message out of the popup queue', async (message) => {
    const result = await notificationFor(message);

    expect(result.priority).toBe(Priority.BULK);
    expect(result.action).toBeUndefined();
    expect(createNotification(1, result).display).toBe(false);
  });

  describe('rejected credentials', () => {
    it('should raise the row of the exchange account and create no notification', async () => {
      const { raised } = storeToRefs(useRaisedConditionsStore());

      const result = await createUserMessageHandler(mockT).handle(authFailure('binance', 'main'));

      expect(result).toBeNull();
      expect(Object.values(get(raised))).toEqual([
        { kind: RaisedConditionKind.EXCHANGE_KEY_REJECTED, location: 'binance', name: 'main' },
      ]);
    });

    it('should raise the premium row for premium credentials and create no notification', async () => {
      const { raised } = storeToRefs(useRaisedConditionsStore());

      const result = await createUserMessageHandler(mockT).handle(authFailure('rotki_premium', null));

      expect(result).toBeNull();
      expect(Object.values(get(raised))).toEqual([
        { cause: PremiumInactiveCause.EXPIRED, kind: RaisedConditionKind.PREMIUM_INACTIVE },
      ]);
    });

    it('should raise the missing key row of an external service and create no notification', async () => {
      const { raised } = storeToRefs(useRaisedConditionsStore());

      const result = await createUserMessageHandler(mockT).handle(authFailure('beaconchain', null));

      expect(result).toBeNull();
      expect(Object.values(get(raised))).toEqual([
        { kind: RaisedConditionKind.MISSING_API_KEY, service: 'beaconchain' },
      ]);
    });
  });
});
