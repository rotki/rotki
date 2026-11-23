import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import CostBasisSpendDetails from '@/modules/history/cost-basis/CostBasisSpendDetails.vue';
import { CostBasisDirection, type CostBasisLot, type CostBasisSpend } from '@/modules/history/cost-basis/types';

const stubs = {
  AssetAmountDisplay: { props: ['amount'], template: '<span class="amount">{{ amount.toString() }}</span>' },
  CostBasisBucketLabel: { template: '<div class="bucket" />' },
  DateDisplay: { props: ['timestamp'], template: '<span class="date">{{ timestamp }}</span>' },
  FiatDisplay: { props: ['value', 'pnl', 'format'], template: '<span class="fiat" :data-pnl="pnl" :data-decimals="format?.decimals" :data-no-mark="format?.noRoundingMark">{{ value.toString() }}</span>' },
  RouterLink: { props: ['to'], template: '<a :data-group="to.query.targetGroupIdentifier" :data-event="to.query.highlightedAccountingEvent" :data-overlay="to.query.overlay"><slot /></a>' },
  RuiChip: { template: '<span><slot /></span>' },
  RuiDivider: true,
  RuiIcon: true,
};

const lot: CostBasisLot = {
  acquiredAt: 1000,
  acquisition: { groupIdentifier: '0xgroup', identifier: 12, location: 'ethereum', locationLabel: '0xA', timestamp: 1_000_000 },
  amount: bigNumberify('0.5'),
  basisPerUnit: bigNumberify('1000'),
  lotId: '12',
  taxable: true,
};

function mountDetails(overrides: Partial<CostBasisSpend> = {}, amount = bigNumberify('0.5')): VueWrapper {
  const entry: CostBasisSpend = {
    asset: 'ETH',
    basisRemaining: bigNumberify('250'),
    basisRemoved: bigNumberify('500'),
    direction: CostBasisDirection.SPEND,
    location: 'ethereum',
    locationLabel: '0xA',
    lots: [lot],
    method: 'fifo',
    proceeds: bigNumberify('900'),
    protocol: null,
    realizedPnl: bigNumberify('400'),
    taxfreePnl: bigNumberify('0'),
    ...overrides,
  };
  return mount(CostBasisSpendDetails, { global: { stubs }, props: { amount, entry } });
}

function figure(wrapper: VueWrapper, key: string): string | undefined {
  const row = wrapper.find(`[data-testid=cost-basis-${key}] .fiat`);
  return row.exists() ? row.text() : undefined;
}

describe('costBasisSpendDetails.vue', () => {
  it('should show the cost basis per unit, cost value and taxable gain of a disposal', () => {
    const wrapper = mountDetails();
    expect(figure(wrapper, 'basis')).toBe('1000');
    expect(figure(wrapper, 'cost-value')).toBe('500');
    expect(figure(wrapper, 'gain')).toBe('400');
    expect(figure(wrapper, 'proceeds')).toBeUndefined();
    expect(figure(wrapper, 'remaining')).toBeUndefined();
    expect(wrapper.get('[data-testid=cost-basis-gain] .fiat').attributes('data-pnl')).toBe('true');
    wrapper.findAll('.fiat').forEach((fiat) => {
      expect(fiat.attributes('data-decimals')).toBe('2');
      expect(fiat.attributes('data-no-mark')).toBe('true');
    });
  });

  it('should weight the cost basis per unit across multiple lots', () => {
    const secondLot: CostBasisLot = { ...lot, acquiredAt: 2000, amount: bigNumberify('1.5'), basisPerUnit: bigNumberify('2000'), lotId: '13' };
    const wrapper = mountDetails({ basisRemoved: bigNumberify('3500'), lots: [lot, secondLot] }, bigNumberify('2'));
    expect(figure(wrapper, 'basis')).toBe('1750');
    expect(figure(wrapper, 'cost-value')).toBe('3500');
  });

  it('should leave the tax free gain out when there is none and show it when there is', () => {
    expect(figure(mountDetails(), 'taxfree-gain')).toBeUndefined();
    expect(figure(mountDetails({ taxfreePnl: null }), 'taxfree-gain')).toBeUndefined();
    expect(figure(mountDetails({ taxfreePnl: bigNumberify('60') }), 'taxfree-gain')).toBe('60');
  });

  it('should show no gain for a move between own accounts or an unpriced spend', () => {
    const transfer = mountDetails({ proceeds: null, realizedPnl: bigNumberify('0'), taxfreePnl: null });
    expect(figure(transfer, 'gain')).toBeUndefined();
    expect(figure(transfer, 'basis')).toBe('1000');
    expect(figure(transfer, 'cost-value')).toBe('500');

    const unpriced = mountDetails({ proceeds: null, realizedPnl: null, taxfreePnl: null });
    expect(figure(unpriced, 'gain')).toBeUndefined();
    expect(figure(unpriced, 'basis')).toBe('1000');
    expect(figure(unpriced, 'cost-value')).toBe('500');
    expect(figure(mountDetails({ realizedPnl: null }), 'gain')).toBeUndefined();
  });

  it('should list each lot with its acquisition date, amount and basis per unit', () => {
    const wrapper = mountDetails({ lots: [lot, { ...lot, acquiredAt: 2000, amount: bigNumberify('2'), basisPerUnit: bigNumberify('30'), lotId: '13' }] });
    const lots = wrapper.findAll('[data-testid=cost-basis-lot]');
    expect(lots.map(row => row.get('.date').text())).toEqual(['1000', '2000']);
    expect(lots.map(row => row.get('.amount').text())).toEqual(['0.5', '2']);
    expect(lots.map(row => row.get('.fiat').text())).toEqual(['1000', '30']);
  });

  it('should link a lot to the event that acquired it with this overlay on, and not link one whose event is gone', () => {
    const wrapper = mountDetails({ lots: [lot, { ...lot, acquisition: null, lotId: '99' }] });
    const links = wrapper.findAll('[data-testid=cost-basis-lot-link]');
    expect(links).toHaveLength(1);
    expect(links[0].attributes()).toMatchObject({ 'data-event': '12', 'data-group': '0xgroup', 'data-overlay': 'cost_basis' });
  });

  it('should mark only the lots held past the tax free period', () => {
    const wrapper = mountDetails({ lots: [lot, { ...lot, lotId: '13', taxable: false }] });
    expect(wrapper.findAll('[data-testid=cost-basis-lot]').map(row => row.find('[data-testid=cost-basis-lot-taxfree]').exists())).toEqual([false, true]);
  });

  it('should hide the lots section for the average cost basis method', () => {
    expect(mountDetails().find('[data-testid=cost-basis-lots]').exists()).toBe(true);
    expect(mountDetails({ method: 'acb' }).find('[data-testid=cost-basis-lots]').exists()).toBe(false);
    expect(mountDetails({ method: 'acb' }).findAll('[data-testid=cost-basis-lot]')).toHaveLength(0);
  });

  it('should say that nothing is known about the acquisition when no lot was found', () => {
    expect(mountDetails().find('[data-testid=cost-basis-no-lots]').exists()).toBe(false);
    expect(mountDetails({ basisRemoved: bigNumberify('0'), lots: [] }).find('[data-testid=cost-basis-no-lots]').exists()).toBe(true);
  });
});
