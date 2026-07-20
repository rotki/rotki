import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import LiquityStatisticRow from './LiquityStatisticRow.vue';

describe('modules/staking/liquity/LiquityStatisticRow', () => {
  it('should render the plain text label and the default slot', () => {
    const wrapper = mount(LiquityStatisticRow, {
      props: { label: 'Total deposited' },
      slots: { default: '<span class="value">42</span>' },
    });

    expect(wrapper.text()).toContain('Total deposited');
    expect(wrapper.find('.value').text()).toBe('42');
  });

  it('should let the label slot replace the text label', () => {
    const wrapper = mount(LiquityStatisticRow, {
      props: { label: 'ignored' },
      slots: { label: '<span class="custom">Estimated PnL</span>' },
    });

    expect(wrapper.find('.custom').exists()).toBe(true);
    expect(wrapper.text()).not.toContain('ignored');
  });

  it('should render without a label', () => {
    const wrapper = mount(LiquityStatisticRow, {
      slots: { default: '<span>value</span>' },
    });

    expect(wrapper.text()).toContain('value');
  });
});
