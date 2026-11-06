import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import AccountBalanceValue from './AccountBalanceValue.vue';

function renderValue(pending: boolean, hasBalance: boolean, value = 42): VueWrapper {
  return mount(AccountBalanceValue, {
    global: {
      stubs: {
        FiatDisplay: { props: ['value', 'loading'], template: '<span data-testid="fiat">{{ value.toString() }}</span>' },
        RuiIcon: true,
        RuiTooltip: { template: '<div><slot name="activator" /><slot /></div>' },
      },
    },
    props: { hasBalance, includedValue: undefined, loading: false, pending, value: bigNumberify(value) },
  });
}

describe('account balance value', () => {
  it('should show the available value and identify it as partial while another chain is pending', () => {
    const wrapper = renderValue(true, true);

    expect(wrapper.get('[data-testid=usd-value]').text()).toBe('42');
    expect(wrapper.find('[data-testid=account-balance-partial]').exists()).toBe(true);
    expect(wrapper.text()).toContain('account_balances.pending_value');
  });

  it('should not show a zero value before any balance has been queried', () => {
    const wrapper = renderValue(true, false, 0);

    expect(wrapper.find('[data-testid=usd-value]').exists()).toBe(false);
    expect(wrapper.get('[data-testid=account-balance-pending]').text()).toBe('\u{2014}');
  });
});
