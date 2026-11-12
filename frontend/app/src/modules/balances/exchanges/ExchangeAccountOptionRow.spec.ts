import type { ExchangeAccountOption } from '@/modules/balances/exchanges/use-exchange-account-selection';
import { bigNumberify } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import ExchangeAccountOptionRow from './ExchangeAccountOptionRow.vue';

const main: ExchangeAccountOption = { identifier: 'kraken-Main', loaded: true, name: 'Main', share: '83.33', value: bigNumberify(1500) };

function mountRow(account: ExchangeAccountOption, selected = false): VueWrapper<InstanceType<typeof ExchangeAccountOptionRow>> {
  return mount(ExchangeAccountOptionRow, {
    global: {
      provide: libraryDefaults,
      stubs: {
        FiatDisplay: { props: ['value'], template: '<span data-testid="value">{{ value.toFixed() }}</span>' },
        PercentageDisplay: { props: ['value'], template: '<span>{{ value }}%</span>' },
        RuiTooltip: { template: '<span><slot name="activator" /><span data-testid="tooltip"><slot /></span></span>' },
      },
    },
    props: { account, selected },
  });
}

describe('exchangeAccountOptionRow', () => {
  it('should show the account name, value and share', () => {
    const wrapper = mountRow(main);

    expect(wrapper.text()).toContain('Main');
    expect(wrapper.text()).toContain('1500');
    expect(wrapper.text()).toContain('83.33%');
    expect(wrapper.find('[data-testid=exchange-account-option-failed]').exists()).toBe(false);
  });

  it('should emit the account identifier when clicked, also on its value', async () => {
    const wrapper = mountRow(main);

    await wrapper.find('[data-testid=value]').trigger('click');

    expect(wrapper.emitted('pick')).toEqual([['kraken-Main']]);
  });

  it('should mark a failed account with its error in the tooltip', () => {
    const wrapper = mountRow({ ...main, error: 'Invalid key' });

    expect(wrapper.find('[data-testid=exchange-account-option-failed]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=tooltip]').text()).toContain('Invalid key');
  });

  it('should say an account that never loaded is not loaded, rather than worth nothing', () => {
    const wrapper = mountRow({ ...main, error: 'Invalid key', loaded: false, share: '0.00', value: bigNumberify(0) });

    expect(wrapper.find('[data-testid=exchange-account-option-unknown]').exists()).toBe(true);
    expect(wrapper.text()).not.toContain('0%');
    expect(wrapper.attributes('data-empty')).toBe('false');
  });

  it('should flag a loaded account holding nothing as empty', () => {
    expect(mountRow({ ...main, share: '0.00', value: bigNumberify(0) }).attributes('data-empty')).toBe('true');
    expect(mountRow(main).attributes('data-empty')).toBe('false');
  });
});
