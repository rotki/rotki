import type { ExchangeAccountOption } from '@/modules/balances/exchanges/use-exchange-account-selection';
import { bigNumberify } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import ExchangeAccountPicker from './ExchangeAccountPicker.vue';

function account(name: string, value: number): ExchangeAccountOption {
  return { identifier: `kraken-${name}`, loaded: true, name, share: '0.00', value: bigNumberify(value) };
}

const few: ExchangeAccountOption[] = [account('Main', 1500), account('Bot', 300)];

const many: ExchangeAccountOption[] = [
  account('Main', 9000),
  account('Trading bot', 800),
  account('Grid bot', 700),
  account('Savings', 600),
  account('DCA weekly', 500),
  account('OTC desk', 400),
  account('Futures hedge', 300),
];

function mountPicker(accounts: ExchangeAccountOption[], modelValue?: string): VueWrapper<InstanceType<typeof ExchangeAccountPicker>> {
  return mount(ExchangeAccountPicker, {
    global: {
      provide: libraryDefaults,
      stubs: {
        FiatDisplay: { props: ['value'], template: '<span>{{ value.toFixed() }}</span>' },
        PercentageDisplay: { props: ['value'], template: '<span>{{ value }}%</span>' },
        RuiMenu: { template: '<div><slot name="activator" :attrs="{}" /><slot /></div>' },
      },
    },
    props: { accounts, modelValue, total: bigNumberify(1750) },
  });
}

function options(wrapper: VueWrapper): (string | undefined)[] {
  return wrapper.findAll('[data-testid=exchange-account-option]').map(option => option.attributes('data-account'));
}

function option(wrapper: VueWrapper, identifier: string): ReturnType<VueWrapper['find']> {
  return wrapper.find(`[data-testid=exchange-account-option][data-account="${identifier}"]`);
}

describe('exchangeAccountPicker', () => {
  it('should leave the button named by its text, so the picked account is announced', () => {
    expect(mountPicker(few, 'kraken-Bot').find('[data-testid=exchange-account-picker]').attributes('aria-label')).toBeUndefined();
  });

  it('should name all accounts on the button when none is picked, and the picked one otherwise', () => {
    expect(mountPicker(few).find('[data-testid=exchange-account-picker]').text()).toContain('exchange_balances.accounts.all');
    expect(mountPicker(few, 'kraken-Bot').find('[data-testid=exchange-account-picker]').text()).toContain('Bot');
  });

  it('should list all accounts first, with the exchange total it is given, then each account in the order given', () => {
    const wrapper = mountPicker(few);

    expect(options(wrapper)).toEqual(['all', 'kraken-Main', 'kraken-Bot']);
    expect(option(wrapper, 'all').text()).toContain('1750');
  });

  it('should mark only the picked option as pressed', () => {
    const wrapper = mountPicker(few, 'kraken-Bot');

    expect(option(wrapper, 'kraken-Bot').attributes('aria-pressed')).toBe('true');
    expect(option(wrapper, 'kraken-Main').attributes('aria-pressed')).toBe('false');
    expect(option(wrapper, 'all').attributes('aria-pressed')).toBe('false');
  });

  it('should emit the identifier of the option clicked, and undefined for all accounts', async () => {
    const wrapper = mountPicker(few, 'kraken-Main');

    await option(wrapper, 'kraken-Bot').trigger('click');
    await option(wrapper, 'all').trigger('click');

    expect(wrapper.emitted('update:modelValue')).toEqual([['kraken-Bot'], [undefined]]);
  });

  it('should offer no search for a handful of accounts', () => {
    expect(mountPicker(few).find('[data-testid=exchange-account-search]').exists()).toBe(false);
  });

  describe('with many accounts', () => {
    it('should narrow the list to the accounts whose name matches, without the all option', async () => {
      const wrapper = mountPicker(many);

      await wrapper.find('[data-testid=exchange-account-search] input').setValue('BOT');

      expect(options(wrapper)).toEqual(['kraken-Trading bot', 'kraken-Grid bot']);
      expect(wrapper.find('[data-testid=exchange-account-section]').text()).toBe('exchange_balances.accounts.section::2');
    });

    it('should say when no account matches', async () => {
      const wrapper = mountPicker(many);

      await wrapper.find('[data-testid=exchange-account-search] input').setValue('nothing like it');

      expect(options(wrapper)).toEqual([]);
      expect(wrapper.find('[data-testid=exchange-account-no-match]').exists()).toBe(true);
    });

    it('should pick the first match on enter', async () => {
      const wrapper = mountPicker(many);
      const input = wrapper.find('[data-testid=exchange-account-search] input');

      await input.setValue('bot');
      await input.trigger('keyup', { key: 'Enter' });

      expect(wrapper.emitted('update:modelValue')).toEqual([['kraken-Trading bot']]);
    });
  });
});
