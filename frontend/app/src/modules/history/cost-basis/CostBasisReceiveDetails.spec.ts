import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import CostBasisReceiveDetails from '@/modules/history/cost-basis/CostBasisReceiveDetails.vue';
import { CostBasisDirection, type CostBasisReceive } from '@/modules/history/cost-basis/types';

const stubs = {
  CostBasisBucketLabel: { template: '<div class="bucket" />' },
  FiatDisplay: { props: ['value', 'format'], template: '<span class="fiat" :data-decimals="format?.decimals" :data-no-mark="format?.noRoundingMark">{{ value.toString() }}</span>' },
};

function mountDetails(basisSource: string, amount = bigNumberify('2')): VueWrapper {
  const entry: CostBasisReceive = {
    asset: 'ETH',
    basisPerUnit: bigNumberify('1234.5'),
    basisSource,
    direction: CostBasisDirection.RECEIVE,
    location: 'ethereum',
    locationLabel: '0xA',
    lotIds: ['1'],
    method: 'fifo',
    protocol: null,
  };
  return mount(CostBasisReceiveDetails, { global: { stubs }, props: { amount, entry } });
}

describe('costBasisReceiveDetails.vue', () => {
  it('should show the cost basis per unit and cost value for what was received', () => {
    const wrapper = mountDetails('price_oracle');
    expect(wrapper.get('[data-testid=cost-basis-per-unit]').text()).toBe('1234.5');
    expect(wrapper.get('[data-testid=cost-basis-cost-value]').text()).toBe('2469');
    wrapper.findAll('.fiat').forEach((fiat) => {
      expect(fiat.attributes('data-decimals')).toBe('2');
      expect(fiat.attributes('data-no-mark')).toBe('true');
    });
  });

  it.each([
    ['event_amount', 'cost_basis_overlay.source.event_amount'],
    ['price_oracle', 'cost_basis_overlay.source.price_oracle'],
    ['transfer_in', 'cost_basis_overlay.source.transfer_in'],
    ['zero_cost', 'cost_basis_overlay.source.zero_cost'],
    ['free_acquisition', 'cost_basis_overlay.source.free_acquisition'],
    ['something_new', 'something_new'],
  ])('should explain a basis from %s', (basisSource, explanation) => {
    expect(mountDetails(basisSource).get('[data-testid=cost-basis-source]').text()).toBe(explanation);
  });
});
