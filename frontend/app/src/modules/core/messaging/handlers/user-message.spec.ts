import type { UserMessageData } from '@/modules/core/messaging/types/base';
import type { BackendProblem } from '@/modules/core/notifications/problems/backend-problem-tree';
import { createCustomPinia } from '@test/utils/create-pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { createUserMessageHandler } from '@/modules/core/messaging/handlers/user-message';
import { useBackendProblemsStore } from '@/modules/core/notifications/problems/use-backend-problems-store';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';
import {
  PremiumInactiveCause,
  RaisedConditionKind,
  useRaisedConditionsStore,
} from '@/modules/shell/action-center/use-raised-conditions-store';

const { loadKeys } = vi.hoisted(() => ({ loadKeys: vi.fn<() => Promise<void>>(async () => {}) }));

vi.mock('@/modules/settings/api-keys/external/use-external-api-keys', () => ({
  useExternalApiKeys: vi.fn(() => ({ load: loadKeys })),
}));

const badData: UserMessageData = {
  fields: { error: 'Missing key: amount', record: 'balance' },
  group: ['error', 'bad_data', 'kucoin', 'balance'],
  key: 'bad_data',
  subject: 'kucoin',
  value: 'Failed to deserialize a kucoin balance. Ignoring it.',
  verbosity: 'error',
};

const badTrade: UserMessageData = {
  ...badData,
  fields: { error: 'Missing key: rate', record: 'trade' },
  group: ['error', 'bad_data', 'kucoin', 'trade'],
  value: 'Failed to deserialize a kucoin trade. Ignoring it.',
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
    loadKeys.mockClear();
    setActivePinia(createCustomPinia());
    useLocationStore().$patch({ allLocations: { binance: { isExchange: true } } });
  });

  function problems(): BackendProblem[] {
    return get(storeToRefs(useBackendProblemsStore()).problems);
  }

  it('should file a message as a backend problem and create no notification', async () => {
    const result = await createUserMessageHandler().handle(badData);

    expect(result).toBeNull();
    expect(get(storeToRefs(useNotificationsStore()).data)).toEqual([]);
    expect(problems()).toMatchObject([{
      id: JSON.stringify(['error', 'bad_data', 'kucoin']),
      items: [{ identity: JSON.stringify(badData.group), repeats: 1, source: badData }],
    }]);
  });

  it('should file two records of one family and location as two items under one parent', async () => {
    const handler = createUserMessageHandler();

    await handler.handle(badData);
    await handler.handle(badTrade);

    expect(problems()).toHaveLength(1);
    expect(problems()[0].items.map(({ source }) => source.value)).toEqual(expect.arrayContaining([badData.value, badTrade.value]));
  });

  it('should count every send the backend held and date the item by the last one', async () => {
    const lastSent = new Date('2026-09-30T07:00:00Z');

    await createUserMessageHandler().handle(badData, { count: 3, lastSent });

    expect(problems()[0].items).toMatchObject([{ lastSeen: lastSent, repeats: 3 }]);
  });

  describe('rejected credentials', () => {
    it('should raise the row of the exchange account and file nothing', async () => {
      const { raised } = storeToRefs(useRaisedConditionsStore());

      const result = await createUserMessageHandler().handle(authFailure('binance', 'main'));

      expect(result).toBeNull();
      expect(problems()).toEqual([]);
      expect(Object.values(get(raised))).toEqual([
        { kind: RaisedConditionKind.EXCHANGE_KEY_REJECTED, location: 'binance', name: 'main' },
      ]);
    });

    it('should raise the premium row for premium credentials', async () => {
      const { raised } = storeToRefs(useRaisedConditionsStore());

      await createUserMessageHandler().handle(authFailure('rotki_premium', null));

      expect(Object.values(get(raised))).toEqual([
        { cause: PremiumInactiveCause.EXPIRED, kind: RaisedConditionKind.PREMIUM_INACTIVE },
      ]);
    });

    it('should raise the missing key row of an external service', async () => {
      const { raised } = storeToRefs(useRaisedConditionsStore());

      await createUserMessageHandler().handle(authFailure('beaconchain', null));

      expect(Object.values(get(raised))).toEqual([
        { kind: RaisedConditionKind.MISSING_API_KEY, service: 'beaconchain' },
      ]);
    });

    it('should reload the saved keys for a service key the backend removed, so its row can open', async () => {
      await createUserMessageHandler().handle(authFailure('beaconchain', null));

      expect(loadKeys).toHaveBeenCalledOnce();
    });

    it('should not reload the service keys for premium or exchange credentials', async () => {
      const handler = createUserMessageHandler();
      await handler.handle(authFailure('rotki_premium', null));
      await handler.handle(authFailure('binance', 'main'));

      expect(loadKeys).not.toHaveBeenCalled();
    });
  });
});
