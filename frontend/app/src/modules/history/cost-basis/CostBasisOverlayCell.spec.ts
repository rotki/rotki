import type { CostBasisStatus, UseCostBasisOverlayReturn } from '@/modules/history/cost-basis/use-cost-basis-overlay';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { bigNumberify } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import CostBasisOverlayCell from '@/modules/history/cost-basis/CostBasisOverlayCell.vue';
import { CostBasisDirection, type CostBasisEntry } from '@/modules/history/cost-basis/types';
import { provideCostBasisOverlay } from '@/modules/history/cost-basis/use-cost-basis-overlay-context';

const stubs = {
  CostBasisReceiveDetails: { template: '<div class="receive-details" />' },
  CostBasisSpendDetails: { template: '<div class="spend-details" />' },
  FiatDisplay: { props: ['value', 'pnl', 'format'], template: '<span class="fiat" :data-decimals="format?.decimals" :data-no-mark="format?.noRoundingMark">{{ value.toString() }}</span>' },
  RuiButton: { template: '<button><slot /></button>' },
  RuiDivider: true,
  RuiIcon: true,
  RuiMenu: { template: '<div class="menu"><slot name="activator" :attrs="{}" /><slot /></div>' },
  RuiSkeletonLoader: { template: '<div class="skeleton" />' },
  RuiTooltip: { template: '<div><slot name="activator" /><slot /></div>' },
};

const bucket = { asset: 'ETH', location: 'ethereum', locationLabel: '0xA', method: 'fifo', protocol: null };

const spend: CostBasisEntry = {
  ...bucket,
  basisRemaining: bigNumberify('0'),
  basisRemoved: bigNumberify('500'),
  direction: CostBasisDirection.SPEND,
  lots: [],
  proceeds: bigNumberify('900'),
  realizedPnl: bigNumberify('400'),
  taxfreePnl: bigNumberify('0'),
};

const receive: CostBasisEntry = {
  ...bucket,
  basisPerUnit: bigNumberify('50'),
  basisSource: 'price_oracle',
  direction: CostBasisDirection.RECEIVE,
  lotIds: ['1'],
};

function mountCell(opts: {
  enabled?: boolean;
  entries?: CostBasisEntry[];
  status?: CostBasisStatus;
  overlay?: Partial<UseCostBasisOverlayReturn>;
} = {}): VueWrapper {
  const entries = opts.entries ?? [];
  const overlay: UseCostBasisOverlayReturn = {
    entriesFor: () => entries,
    refresh: async () => {},
    refreshProcessing: async () => {},
    registerEvent: () => () => {},
    statusFor: () => opts.status ?? (entries.length > 0 ? 'ready' : 'empty'),
    ...opts.overlay,
  };
  const event = createMock<HistoryEventEntry>({ amount: bigNumberify('2'), identifier: 123 });
  const host = defineComponent({
    setup() {
      provideCostBasisOverlay({ enabled: ref<boolean>(opts.enabled ?? true), overlay });
      return (): VNode => h(CostBasisOverlayCell, { event });
    },
  });
  return mount(host, { global: { stubs } });
}

describe('costBasisOverlayCell.vue', () => {
  it('should render nothing while the overlay is off', () => {
    expect(mountCell({ enabled: false, entries: [spend] }).find('[data-testid=cost-basis-overlay-cell]').exists()).toBe(false);
  });

  it('should look up and register its event, and release it on unmount', () => {
    const cleanup = vi.fn<() => void>();
    const registerEvent = vi.fn<(identifier: number) => () => void>(() => cleanup);
    const entriesFor = vi.fn<(identifier: number) => CostBasisEntry[]>(() => [spend]);
    const wrapper = mountCell({ overlay: { entriesFor, registerEvent } });
    expect(registerEvent).toHaveBeenCalledExactlyOnceWith(123);
    expect(entriesFor).toHaveBeenCalledWith(123);
    wrapper.unmount();
    expect(cleanup).toHaveBeenCalledOnce();
  });

  it('should show a placeholder while loading and an error when the fetch failed', () => {
    expect(mountCell({ status: 'loading' }).find('.skeleton').exists()).toBe(true);
    expect(mountCell({ status: 'error' }).find('[data-testid=cost-basis-error]').exists()).toBe(true);
  });

  it('should say that an event without entries does not change any cost basis', () => {
    const wrapper = mountCell({ entries: [] });
    expect(wrapper.find('[data-testid=cost-basis-empty]').exists()).toBe(true);
    expect(wrapper.find('.menu').exists()).toBe(false);
  });

  it('should show pending processing and hide any figures until the event is processed', async () => {
    const status = ref<CostBasisStatus>('processing');
    const entries = ref<CostBasisEntry[]>([spend]);
    const wrapper = mountCell({ overlay: { entriesFor: () => get(entries), statusFor: () => get(status) } });

    expect(wrapper.get('[data-testid=cost-basis-pending]').text()).toContain('cost_basis_overlay.processing');
    expect(wrapper.find('[data-testid=cost-basis-pnl]').exists()).toBe(false);
    expect(wrapper.text()).not.toContain('cost_basis_overlay.no_data');

    set(entries, []);
    set(status, 'empty');
    await nextTick();
    expect(wrapper.get('[data-testid=cost-basis-empty]').text()).toContain('cost_basis_overlay.no_data');

    set(entries, [spend]);
    set(status, 'ready');
    await nextTick();
    expect(wrapper.get('[data-testid=cost-basis-pnl]').text()).toBe('400');
    expect(wrapper.find('[data-testid=cost-basis-empty]').exists()).toBe(false);
  });

  it('should show the gain of a disposal above its basis, with the spend details behind it', () => {
    const wrapper = mountCell({ entries: [spend] });
    expect(wrapper.get('[data-testid=cost-basis-pnl]').text()).toBe('400');
    expect(wrapper.get('[data-testid=cost-basis-basis]').text()).toContain('500');
    expect(wrapper.get('[data-testid=cost-basis-basis]').text()).toContain('cost_basis_overlay.labels.disposal');
    wrapper.findAll('.fiat').forEach((fiat) => {
      expect(fiat.attributes('data-decimals')).toBe('2');
      expect(fiat.attributes('data-no-mark')).toBe('true');
    });
    expect(wrapper.findAll('.spend-details')).toHaveLength(1);
    expect(wrapper.find('.receive-details').exists()).toBe(false);
  });

  it('should show the cost of an acquisition for the amount of the event and no gain', () => {
    const wrapper = mountCell({ entries: [receive] });
    expect(wrapper.find('[data-testid=cost-basis-pnl]').exists()).toBe(false);
    expect(wrapper.get('[data-testid=cost-basis-basis]').text()).toContain('100');
    expect(wrapper.get('[data-testid=cost-basis-basis]').text()).toContain('cost_basis_overlay.labels.acquisition');
    expect(wrapper.findAll('.receive-details')).toHaveLength(1);
  });

  it('should show a move between own accounts as moved basis with no gain, and both sides in the details', () => {
    const wrapper = mountCell({ entries: [spend, receive] });
    expect(wrapper.find('[data-testid=cost-basis-pnl]').exists()).toBe(false);
    expect(wrapper.get('[data-testid=cost-basis-basis]').text()).toContain('cost_basis_overlay.labels.transfer');
    expect(wrapper.findAll('.spend-details')).toHaveLength(1);
    expect(wrapper.findAll('.receive-details')).toHaveLength(1);
  });
});
