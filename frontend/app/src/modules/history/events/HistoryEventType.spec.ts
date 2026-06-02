import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { HistoryEventAccountingRuleStatus, type HistoryEventEntry } from '@/modules/history/events/schemas';
import HistoryEventType from './HistoryEventType.vue';

vi.mock('@/modules/history/events/mapping/use-history-event-mappings', () => ({
  useHistoryEventMappings: vi.fn().mockReturnValue({
    getEventTypeData: (): ComputedRef<{ label: string; icon: string; color: string; identifier: string }> =>
      computed(() => ({ color: 'primary', icon: 'lu-circle', identifier: 'transfer', label: 'Transfer' })),
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn().mockReturnValue({
    // Treat blockchains as matched, exchanges (e.g. kraken) as unmatched.
    matchChain: (location: string): string | undefined =>
      ['ethereum', 'optimism'].includes(location) ? location : undefined,
  }),
}));

describe('history/events/HistoryEventType', () => {
  let pinia: Pinia;

  const stubs = {
    HistoryEventTypeCombination: { template: '<div data-testid="combination" />' },
    HistoryEventTypeCounterparty: {
      props: ['counterparty', 'address', 'location'],
      template: '<div data-testid="counterparty-badge"><slot /></div>',
    },
    HistoryEventTypeLocationBadge: {
      props: ['location'],
      template: '<div data-testid="location-badge"><slot /></div>',
    },
    HistoryEventAccount: { template: '<div />' },
    HistoryEventStateChip: { template: '<div />' },
  };

  const commonFields = {
    amount: bigNumberify('100'),
    asset: 'ETH',
    eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.PROCESSED,
    eventSubtype: 'spend',
    eventType: 'withdrawal',
    groupIdentifier: 'group1',
    hidden: false,
    identifier: 1,
    ignoredInAccounting: false,
    locationLabel: 'Account 1',
    sequenceIndex: 0,
    states: [],
    timestamp: 1000000,
  };

  function createEvmEvent(location: string, counterparty: string | null): HistoryEventEntry {
    return {
      ...commonFields,
      address: null,
      counterparty,
      entryType: HistoryEventEntryType.EVM_EVENT,
      extraData: null,
      location,
      txRef: 'tx1',
    };
  }

  function createAssetMovement(location: string): HistoryEventEntry {
    return {
      ...commonFields,
      entryType: HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
      extraData: null,
      location,
    };
  }

  function createOnlineEvent(location: string): HistoryEventEntry {
    return {
      ...commonFields,
      entryType: HistoryEventEntryType.HISTORY_EVENT,
      location,
    };
  }

  function createWrapper(
    event: HistoryEventEntry,
    matchedMovement?: boolean,
  ): VueWrapper<InstanceType<typeof HistoryEventType>> {
    return mount(HistoryEventType, {
      global: { plugins: [pinia], stubs },
      props: { event, matchedMovement },
    });
  }

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  it('should show the location badge on the exchange-side asset movement of a matched movement', () => {
    const wrapper = createWrapper(createAssetMovement('kraken'), true);

    expect(wrapper.find('[data-testid="location-badge"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="counterparty-badge"]').exists()).toBe(false);
  });

  it('should show the chain icon and suppress the counterparty badge on the on-chain leg of a matched movement', () => {
    const wrapper = createWrapper(createEvmEvent('optimism', 'kraken'), true);

    expect(wrapper.find('[data-testid="counterparty-badge"]').exists()).toBe(false);
    const badge = wrapper.find('[data-testid="location-badge"]');
    expect(badge.exists()).toBe(true);
    expect(wrapper.findComponent(stubs.HistoryEventTypeLocationBadge).props('location')).toBe('optimism');
  });

  it('should still show the counterparty badge for a normal on-chain event (not a matched movement)', () => {
    const wrapper = createWrapper(createEvmEvent('optimism', 'kraken'), false);

    expect(wrapper.find('[data-testid="counterparty-badge"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="location-badge"]').exists()).toBe(false);
  });

  it('should not show the location badge for a non-asset-movement event on an exchange', () => {
    const wrapper = createWrapper(createOnlineEvent('kraken'), true);

    expect(wrapper.find('[data-testid="location-badge"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="counterparty-badge"]').exists()).toBe(false);
  });
});
