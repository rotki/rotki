import type { BankAccountBalance } from '@/modules/banks/types';
import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import BankAccountsTable from '@/modules/banks/components/BankAccountsTable.vue';

const stubs = {
  AssetDetails: { props: ['asset'], template: '<span data-testid="asset">{{ asset }}</span>' },
  FiatDisplay: { props: ['value'], template: '<span data-testid="value">{{ value.toFixed() }}</span>' },
  RuiDataTable: {
    props: ['rows'],
    template: '<div><div v-for="row in rows" :key="row.identifier" data-testid="row"><slot name="item.name" :row="row" /><slot name="item.asset" :row="row" /><slot name="item.amount" :row="row" /><slot name="item.value" :row="row" /></div></div>',
  },
  ValueDisplay: { props: ['value', 'format'], template: '<span data-testid="amount" :data-format="JSON.stringify(format)">{{ value.toFixed() }}</span>' },
};

function account(identifier: string, name: string, iban: string | null, amount: number, asset = 'EUR'): BankAccountBalance {
  return { amount: bigNumberify(amount), asset, iban, identifier, name, value: bigNumberify(amount) };
}

const checking = account('a', 'DE02120300000000202051', 'DE02120300000000202051', 100.25);
const savings = account('b', 'Tagesgeld', 'DE02120300000000202052', 900.5);
const dollars = account('c', '202053', null, 7, 'USD');

function createWrapper(props: { accounts?: BankAccountBalance[]; search?: string } = {}): VueWrapper<InstanceType<typeof BankAccountsTable>> {
  return mount(BankAccountsTable, {
    global: { stubs },
    props: { accounts: [savings, checking, dollars], ...props },
  });
}

function accountIds(wrapper: VueWrapper): (string | undefined)[] {
  return wrapper.findAll('[data-testid=bank-account]').map(item => item.attributes('data-account'));
}

describe('modules/banks/components/BankAccountsTable', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
  });

  it('should list every account with its currency, amount to the cent and value', () => {
    const wrapper = createWrapper();
    const row = wrapper.findAll('[data-testid=row]')[0];

    expect(accountIds(wrapper)).toEqual(['b', 'a', 'c']);
    expect(row.find('[data-testid=asset]').text()).toBe('EUR');
    expect(row.find('[data-testid=amount]').text()).toBe('900.5');
    expect(JSON.parse(row.find('[data-testid=amount]').attributes('data-format') ?? '')).toEqual({ decimals: 2 });
    expect(row.find('[data-testid=value]').text()).toBe('900.5');
  });

  it('should name an account by its IBAN once, and put the IBAN under an account with a name of its own', () => {
    const wrapper = createWrapper();
    const [named, byIban] = wrapper.findAll('[data-testid=bank-account]');

    expect(named.text()).toContain('Tagesgeld');
    expect(named.find('[data-testid=bank-account-iban]').text()).toBe('DE02 1203 0000 0000 2020 52');
    expect(byIban.text()).toBe('DE02 1203 0000 0000 2020 51');
    expect(byIban.find('[data-testid=bank-account-iban]').exists()).toBe(false);
  });

  it('should narrow the accounts by name, by IBAN however it is spaced, and by currency', () => {
    expect(accountIds(createWrapper({ search: 'tages' }))).toEqual(['b']);
    expect(accountIds(createWrapper({ search: '2020 51' }))).toEqual(['a']);
    expect(accountIds(createWrapper({ search: 'usd' }))).toEqual(['c']);
    expect(accountIds(createWrapper({ search: '  ' }))).toEqual(['b', 'a', 'c']);
  });
});
