import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import CostBasisReceiveDetails from '@/modules/history/cost-basis/CostBasisReceiveDetails.vue';
import { CostBasisDirection, type CostBasisReceive } from '@/modules/history/cost-basis/types';

const stubs = {
  CostBasisBucketLabel: { template: '<div class="bucket" />' },
  FiatDisplay: { props: ['value'], template: '<span class="fiat">{{ value.toString() }}</span>' },
};

function mountDetails(basisSource: string): VueWrapper {
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
  return mount(CostBasisReceiveDetails, { global: { stubs }, props: { entry } });
}

describe('costBasisReceiveDetails.vue', () => {
  it('should show the basis of each unit received', () => {
    expect(mountDetails('price_oracle').get('[data-testid=cost-basis-per-unit]').text()).toBe('1234.5');
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
