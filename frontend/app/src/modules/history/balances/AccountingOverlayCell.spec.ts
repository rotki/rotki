import type { PairOverlayStatus, UseAccountingOverlayReturn } from '@/modules/history/balances/use-accounting-overlay';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { type ComputedRef, defineComponent, h, type VNode } from 'vue';
import AccountingOverlayCell from '@/modules/history/balances/AccountingOverlayCell.vue';
import { type AccountingOverlayContext, provideAccountingOverlay } from '@/modules/history/balances/use-accounting-overlay-context';

// Drives the direction arrow; `mock`-prefixed so it can be read inside the hoisted factory.
let mockDirection: 'in' | 'out' | 'neutral' = 'neutral';

interface EventTypeData { color: string; direction: string; icon: string }

vi.mock('@/modules/history/events/mapping/use-history-event-mappings', () => ({
  useHistoryEventMappings: (): { getEventTypeData: () => ComputedRef<EventTypeData> } => ({
    getEventTypeData: (): ComputedRef<EventTypeData> => computed(() => ({ color: 'success', direction: mockDirection, icon: 'lu-arrow-down' })),
  }),
}));

const stubs = {
  AccountingOverlayBuckets: { props: ['eventLocation', 'eventProtocol'], template: '<div class="buckets" :data-location="eventLocation" :data-protocol="eventProtocol ?? \'\'" />' },
  AccountingOverlaySparkline: { template: '<div class="sparkline" />' },
  AssetAmountDisplay: { props: ['amount', 'asset'], template: '<span class="amount">{{ amount?.toString() }}</span>' },
  RuiButton: { template: '<button class="button"><slot /></button>' },
  RuiIcon: { template: '<i class="icon" />' },
  RuiMenu: { template: '<div class="menu"><slot name="activator" /><slot /></div>' },
  RuiSkeletonLoader: { template: '<div class="skeleton" />' },
  RuiTooltip: { template: '<div class="tooltip"><slot name="activator" /><slot /></div>' },
};

function event(locationLabel: string | null, counterparty?: string | null): HistoryEventEntry {
  return { amount: bigNumberify('2'), asset: 'ETH', counterparty, location: 'ethereum', locationLabel, timestamp: 150_000 } as HistoryEventEntry;
}

function mountCell(opts: {
  enabled: boolean;
  status?: PairOverlayStatus;
  balance?: string;
  locationLabel?: string | null;
  counterparty?: string | null;
  direction?: 'in' | 'out' | 'neutral';
}): VueWrapper {
  mockDirection = opts.direction ?? 'neutral';
  const overlay: UseAccountingOverlayReturn = {
    balanceAfter: () => opts.balance === undefined ? undefined : bigNumberify(opts.balance),
    bucketsAt: () => [],
    ensurePair: () => {},
    refresh: async () => {},
    refreshProcessing: () => {},
    seriesUpTo: () => [],
    state: computed(() => 'ready'),
    statusFor: () => opts.status ?? 'ready',
  };
  const context: AccountingOverlayContext = { enabled: ref(opts.enabled), overlay };

  const host = defineComponent({
    setup() {
      provideAccountingOverlay(context);
      return (): VNode => h(AccountingOverlayCell, { event: event(opts.locationLabel ?? '0xA', opts.counterparty) });
    },
  });

  return mount(host, { global: { stubs } });
}

describe('accountingOverlayCell.vue', () => {
  it('should render nothing when the overlay is disabled', () => {
    const wrapper = mountCell({ enabled: false });
    expect(wrapper.find('[data-testid=accounting-overlay-cell]').exists()).toBe(false);
  });

  it('should render the balance amount when ready', () => {
    const wrapper = mountCell({ balance: '12.5', enabled: true, status: 'ready' });
    expect(wrapper.find('[data-testid=accounting-overlay-cell]').exists()).toBe(true);
    expect(wrapper.find('.amount').text()).toBe('12.5');
  });

  it('should show a delta line for non-neutral events', () => {
    const wrapper = mountCell({ balance: '5', direction: 'in', enabled: true, status: 'ready' });
    expect(wrapper.find('[data-testid=overlay-delta]').exists()).toBe(true);
  });

  it('should not show a delta line for neutral events', () => {
    const wrapper = mountCell({ balance: '5', direction: 'neutral', enabled: true, status: 'ready' });
    expect(wrapper.find('[data-testid=overlay-delta]').exists()).toBe(false);
  });

  it('should render a skeleton while loading', () => {
    const wrapper = mountCell({ enabled: true, status: 'loading' });
    expect(wrapper.find('.skeleton').exists()).toBe(true);
    expect(wrapper.find('.amount').exists()).toBe(false);
  });

  it('should render a placeholder when the event has no account', () => {
    const wrapper = mountCell({ enabled: true, locationLabel: null, status: 'ready' });
    expect(wrapper.find('[data-testid=accounting-overlay-cell]').exists()).toBe(true);
    expect(wrapper.find('.amount').exists()).toBe(false);
  });

  it('should pass an event counterparty as the bucket protocol to highlight', () => {
    const wrapper = mountCell({ balance: '5', counterparty: 'aave-v3', enabled: true, status: 'ready' });
    expect(wrapper.find('.buckets').attributes('data-protocol')).toBe('aave-v3');
  });

  it('should treat a gas counterparty as the wallet bucket', () => {
    const wrapper = mountCell({ balance: '5', counterparty: 'gas', enabled: true, status: 'ready' });
    expect(wrapper.find('.buckets').attributes('data-protocol')).toBe('');
  });
});
