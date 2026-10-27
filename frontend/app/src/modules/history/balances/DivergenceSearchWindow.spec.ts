import type { HistoricalBalanceDivergenceEvent } from '@/modules/history/balances/types';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import DivergenceSearchWindow from '@/modules/history/balances/DivergenceSearchWindow.vue';

const stubs = {
  RuiIcon: { template: '<i class="icon" />' },
  RuiTooltip: { template: '<span><slot name="activator" /><slot /></span>' },
};

function event(timestamp: number): HistoricalBalanceDivergenceEvent {
  return {
    blockNumber: timestamp % 1000,
    difference: bigNumberify('0'),
    eventIdentifier: 1,
    groupIdentifier: null,
    onchainBalance: bigNumberify('0'),
    timestamp,
    trackedBalance: bigNumberify('0'),
    txHash: null,
  };
}

function createWrapper(from: number, to: number): VueWrapper {
  return mount(DivergenceSearchWindow, {
    global: { stubs },
    props: { from: event(from), to: event(to) },
  });
}

describe('divergenceSearchWindow', () => {
  it('should say how far apart the two events are', () => {
    const wrapper = createWrapper(1790000000, 1790000000 + (82 * 86400));

    expect(wrapper.text()).toContain('balance_divergence.search_window');
    expect(wrapper.text()).toContain('balance_divergence.apart.days');
    expect(wrapper.find('[data-testid=divergence-gap-approximate]').exists()).toBe(false);
  });

  it('should mark a rounded gap as approximate', () => {
    const wrapper = createWrapper(1790000000, 1790000000 + (82 * 86400) + 3600);

    expect(wrapper.find('[data-testid=divergence-gap-approximate]').exists()).toBe(true);
    expect(wrapper.text()).toContain('balance_divergence.apart.rounded');
  });

  it('should name the block range of the window', () => {
    const wrapper = createWrapper(1790000011, 1790000022 + (82 * 86400));

    expect(wrapper.get('[data-testid=divergence-block-range]').text()).toBe('balance_divergence.block_range::11, 822');
  });

  it('should pick the hours label for a gap under a day', () => {
    const wrapper = createWrapper(1790000000, 1790000000 + (5 * 3600));

    expect(wrapper.text()).toContain('balance_divergence.apart.hours');
  });
});
