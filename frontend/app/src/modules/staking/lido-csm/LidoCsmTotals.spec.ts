import type { LidoCsmNodeOperator } from '@/modules/staking/staking-types';
import { bigNumberify } from '@rotki/common';
import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import StakingTotals, { type StakingTotal } from '@/modules/staking/components/StakingTotals.vue';
import LidoCsmTotals from '@/modules/staking/lido-csm/LidoCsmTotals.vue';

function operator(nodeOperatorId: number, pending: string | null): LidoCsmNodeOperator {
  return {
    address: '0x1111111111111111111111111111111111111111',
    metrics: {
      bond: { claimable: bigNumberify('0.5'), current: bigNumberify('2'), required: bigNumberify('2') },
      keys: { totalDeposited: 1 },
      operatorType: { id: 0, label: 'Permissionless' },
      rewards: { pending: pending === null ? null : bigNumberify(pending) },
    },
    nodeOperatorId,
    stakingModuleId: 3,
  };
}

function totalsOf(operators: LidoCsmNodeOperator[]): Record<string, string> {
  const wrapper = mount(LidoCsmTotals, {
    global: { stubs: { StakingTotals: true } },
    props: { loading: false, operators },
  });
  const totals: StakingTotal[] = wrapper.getComponent(StakingTotals).props('totals');
  return Object.fromEntries(totals.map(({ amount, key }) => [key, amount.toString()]));
}

describe('lidoCsmTotals', () => {
  it('should add up the bond, claimable bond and pending rewards of every operator', () => {
    expect(totalsOf([operator(1, '0.25'), operator(2, '0.5')])).toEqual({ bond: '4', claimable: '1', rewards: '0.75' });
  });

  it('should leave pending rewards the backend could not fetch out of the rewards, but keep their bond', () => {
    expect(totalsOf([operator(1, '0.25'), operator(2, null)])).toEqual({ bond: '4', claimable: '1', rewards: '0.25' });
  });
});
