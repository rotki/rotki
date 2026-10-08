import type { HistoryEventTypeData } from '@/modules/history/events/event-type';
import { NotificationKind } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { withSetup } from '@test/utils/with-setup';
import { flushPromises } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';

const getTransactionTypeMappings = vi.fn<() => Promise<HistoryEventTypeData>>();

const { notify } = vi.hoisted(() => ({ notify: vi.fn() }));

vi.mock('@/modules/core/notifications/use-notifications', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useNotifications: (): { notify: typeof notify } => ({ notify }),
}));

vi.mock('@/modules/history/api/events/use-history-events-api', () => ({
  useHistoryEventsApi: (): { getTransactionTypeMappings: typeof getTransactionTypeMappings } => ({
    getTransactionTypeMappings,
  }),
}));

const mappings: HistoryEventTypeData = {
  accountingEventsIcons: {},
  entryTypeMappings: {},
  eventCategoryDetails: {
    'bridge receive': {
      counterpartyMappings: { default: { icon: 'lu-download', label: 'bridge receive' } },
      direction: 'in',
      group: 'bridge',
    },
    'mev reward': {
      counterpartyMappings: { default: { color: 'success', icon: 'lu-zap', label: 'mev reward' } },
      direction: 'in',
      group: 'validator',
    },
    'receive': {
      counterpartyMappings: {
        'aave-v3': { icon: 'lu-coins', label: 'receive from aave' },
        'default': { color: 'success', icon: 'lu-download', label: 'receive' },
      },
      direction: 'in',
      group: 'receive',
    },
  },
  eventCategoryGroups: {},
  globalMappings: {
    informational: {
      'mev reward': { default: 'mev reward' },
    },
    receive: {
      bridge: { default: 'bridge receive' },
      none: { default: 'receive' },
    },
    staking: {
      'mev reward': { default: 'mev reward' },
    },
  },
};

describe('useHistoryEventMappings', () => {
  const wrappers: { unmount: () => void }[] = [];

  beforeEach(() => {
    setActivePinia(createCustomPinia());
    getTransactionTypeMappings.mockResolvedValue(mappings);
  });

  afterEach(() => {
    // the composable is shared, so its state only resets once every user is gone
    while (wrappers.length > 0) wrappers.pop()?.unmount();
    vi.clearAllMocks();
  });

  async function setup(): Promise<ReturnType<typeof useHistoryEventMappings>> {
    const { result, wrapper } = withSetup(() => useHistoryEventMappings());
    wrappers.push(wrapper);
    await flushPromises();
    return result;
  }

  it('should file a failed mappings fetch as a failure, which never pops, since nothing the user did started it', async () => {
    getTransactionTypeMappings.mockRejectedValue(new Error('offline'));

    await setup();

    expect(notify).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({ kind: NotificationKind.FAILURE }));
  });

  describe('findEventTypeData', () => {
    it('should resolve a combination that has no counterparty', async () => {
      const { findEventTypeData } = await setup();

      expect(findEventTypeData({ counterparty: null, eventSubtype: 'bridge', eventType: 'receive' })).toMatchObject({
        direction: 'in',
        identifier: 'bridge receive',
      });
    });

    it('should resolve a combination whose counterparty is an empty string, which the forms use for "none" and callers would otherwise read as unknown', async () => {
      const { findEventTypeData } = await setup();

      expect(findEventTypeData({ counterparty: '', eventSubtype: 'bridge', eventType: 'receive' })).toMatchObject({
        direction: 'in',
        identifier: 'bridge receive',
      });
    });

    it('should keep the category color and direction for an event that moves funds', async () => {
      const { findEventTypeData } = await setup();

      expect(findEventTypeData({ eventSubtype: 'mev reward', eventType: 'staking' })).toMatchObject({
        color: 'success',
        direction: 'in',
        identifier: 'mev reward',
      });
    });

    it('should make an informational event neutral and uncolored, as the backend counts it', async () => {
      const { findEventTypeData } = await setup();
      const data = findEventTypeData({ eventSubtype: 'mev reward', eventType: 'informational' });

      expect(data).toMatchObject({ direction: 'neutral', icon: 'lu-zap', identifier: 'mev reward' });
      expect(data.color).toBeUndefined();
    });

    it('should prefer the counterparty specific details when there are any', async () => {
      const { findEventTypeData } = await setup();

      expect(findEventTypeData({ counterparty: 'aave-v3', eventSubtype: 'none', eventType: 'receive' })).toMatchObject({
        identifier: 'aave-v3',
        label: 'backend_mappings.events.type.receive_from_aave',
      });
    });

    it('should keep the counterparty identifier when only default details exist', async () => {
      const { findEventTypeData } = await setup();

      expect(findEventTypeData({ counterparty: 'hop', eventSubtype: 'bridge', eventType: 'receive' })).toMatchObject({
        identifier: 'hop',
        label: 'backend_mappings.events.type.bridge_receive',
      });
    });

    it('should fall back to an empty identifier for an unmapped combination', async () => {
      const { findEventTypeData } = await setup();

      expect(findEventTypeData({ counterparty: '', eventSubtype: 'reward', eventType: 'receive' })).toMatchObject({
        identifier: '',
        label: 'reward',
      });
    });
  });
});
