import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import BalanceDivergenceToggle from '@/modules/history/balances/BalanceDivergenceToggle.vue';
import { createRuiPlugin } from '@/plugins/rui';

function createWrapper(visible: boolean): VueWrapper<InstanceType<typeof BalanceDivergenceToggle>> {
  return mount(BalanceDivergenceToggle, {
    global: {
      plugins: [createRuiPlugin({})],
    },
    props: { modelValue: visible },
  });
}

describe('balanceDivergenceToggle', () => {
  it('should open the panel when toggled while hidden', async () => {
    const wrapper = createWrapper(false);

    await wrapper.find('[data-testid="balance-divergence-toggle"]').trigger('click');

    expect(wrapper.emitted('update:modelValue')).toEqual([[true]]);
  });

  it('should close the panel when toggled while open', async () => {
    const wrapper = createWrapper(true);

    await wrapper.find('[data-testid="balance-divergence-toggle"]').trigger('click');

    expect(wrapper.emitted('update:modelValue')).toEqual([[false]]);
  });
});
