import type { DivergenceBoundaryEvent } from '@/modules/history/balances/use-balance-divergence';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { defineComponent } from 'vue';
import DivergenceBoundaryCard from '@/modules/history/balances/DivergenceBoundaryCard.vue';

const stubs = {
  AssetAmountDisplay: { props: ['amount', 'asset'], template: '<span class="amount">{{ amount?.toString() }}</span>' },
  HashLink: { props: ['text'], template: '<span class="hash">{{ text }}</span>' },
  RuiButton: defineComponent({
    emits: ['click'],
    props: { disabled: Boolean },
    template: '<button :disabled="disabled" @click="$emit(\'click\')"><slot name="prepend" /><slot /></button>',
  }),
  RuiIcon: { template: '<i class="icon" />' },
};

function boundary(overrides: Partial<DivergenceBoundaryEvent['event']> = {}): DivergenceBoundaryEvent {
  return {
    color: 'success',
    event: {
      blockNumber: 11,
      difference: bigNumberify('0'),
      eventIdentifier: 101,
      groupIdentifier: `1${'a'.repeat(64)}`,
      onchainBalance: bigNumberify('5'),
      timestamp: 100,
      trackedBalance: bigNumberify('5'),
      ...overrides,
    },
    key: 'last_matching',
  };
}

function createWrapper(boundaryEvent: DivergenceBoundaryEvent): VueWrapper {
  return mount(DivergenceBoundaryCard, {
    global: { stubs },
    props: { asset: 'ETH', boundary: boundaryEvent },
  });
}

describe('divergenceBoundaryCard', () => {
  it('should render the truncated group identifier and balances', () => {
    const wrapper = createWrapper(boundary());

    const card = wrapper.find('[data-testid="divergence-last_matching"]');
    expect(card.exists()).toBe(true);
    expect(card.find('.hash').text()).toBe(`1${'a'.repeat(64)}`);
    expect(card.text()).toContain('11');
  });

  it('should emit view when the view button is clicked', async () => {
    const wrapper = createWrapper(boundary());

    await wrapper.find('[data-testid="view-divergence-last_matching"]').trigger('click');

    expect(wrapper.emitted('view')).toHaveLength(1);
  });

  it('should disable the view button when the boundary has no group identifier', () => {
    const wrapper = createWrapper(boundary({ groupIdentifier: null }));

    const button = wrapper.find('[data-testid="view-divergence-last_matching"]');
    expect(button.attributes('disabled')).toBeDefined();
  });
});
