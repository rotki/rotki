import type { BankBalanceData } from '@/modules/banks/use-bank-data';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import BankBalanceCards from '@/modules/banks/components/BankBalanceCards.vue';

const stubs = {
  I18nT: { props: ['keypath'], template: '<div :data-keypath="keypath"><slot name="connector" /> <slot name="time" /></div>' },
  FiatDisplay: { props: ['value', 'loading'], template: '<span data-testid="fiat" :data-loading="loading">{{ value.toFixed() }}</span>' },
  BankConnectorIcon: true,
  PercentageDisplay: { props: ['value'], template: '<span data-testid="percentage">{{ value }}</span>' },
  RouterLink: { props: ['to'], template: '<a :data-to="JSON.stringify(to)"><slot /></a>' },
  RuiIcon: true,
  TimeAgoDisplay: { props: ['timestamp'], template: '<span>ago:{{ timestamp }}</span>' },
};

function bank(name: string, total: number, syncStatus: Partial<BankBalanceData['syncStatus']> = {}): BankBalanceData {
  return {
    accounts: [],
    balances: [],
    connector: 'fints',
    displayName: 'FinTS/HBCI',
    name,
    syncStatus: { authChallenge: null, authExpired: false, lastError: null, lastSyncTs: 100, running: false, ...syncStatus },
    total: bigNumberify(total),
  };
}

function createWrapper(props: { banks: BankBalanceData[]; selected?: string; loading?: boolean; isBankLoading?: (name: string) => boolean }): VueWrapper<InstanceType<typeof BankBalanceCards>> {
  return mount(BankBalanceCards, {
    global: { stubs },
    props: { isBankLoading: (): boolean => false, total: bigNumberify(300), ...props },
  });
}

function card(wrapper: VueWrapper, name: string): ReturnType<VueWrapper['find']> {
  return wrapper.find(`[data-testid=bank-balance-card][data-bank="${name}"]`);
}

describe('modules/banks/components/BankBalanceCards', () => {
  it('should offer all banks first, then one card per bank linking to it', () => {
    const wrapper = createWrapper({ banks: [bank('DKB', 200), bank('ING', 100)] });
    const cards = wrapper.findAll('[data-testid=bank-balance-card]');

    expect(cards.map(item => item.attributes('data-bank'))).toEqual(['all', 'DKB', 'ING']);
    expect(JSON.parse(cards[0].attributes('data-to') ?? '')).toEqual({ name: '/balances/banks/', query: {} });
    expect(JSON.parse(cards[1].attributes('data-to') ?? '')).toEqual({ name: '/balances/banks/', query: { bank: 'DKB' } });
  });

  it('should mark the card of what the page shows as current', () => {
    const all = createWrapper({ banks: [bank('DKB', 200)] });
    expect(card(all, 'all').attributes('aria-current')).toBe('page');
    expect(card(all, 'DKB').attributes('aria-current')).toBeUndefined();

    const one = createWrapper({ banks: [bank('DKB', 200)], selected: 'DKB' });
    expect(card(one, 'all').attributes('aria-current')).toBeUndefined();
    expect(card(one, 'DKB').attributes('aria-current')).toBe('page');
  });

  it('should show each bank total, its share of all banks and the total of all banks', () => {
    const wrapper = createWrapper({ banks: [bank('DKB', 200)] });

    expect(card(wrapper, 'all').find('[data-testid=fiat]').text()).toBe('300');
    expect(card(wrapper, 'DKB').find('[data-testid=fiat]').text()).toBe('200');
    expect(card(wrapper, 'DKB').find('[data-testid=percentage]').text()).toBe('66.67');
  });

  it('should show when a bank that is fine last synced', () => {
    const wrapper = createWrapper({ banks: [bank('DKB', 200)] });
    const status = card(wrapper, 'DKB').find('[data-testid=bank-balance-card-status]');

    expect(status.attributes('data-keypath')).toBe('bank_balances.cards.synced');
    expect(status.text()).toContain('FinTS/HBCI');
    expect(status.text()).toContain('ago:100');
  });

  it('should name only the connector of a bank that never synced', () => {
    const wrapper = createWrapper({ banks: [bank('DKB', 0, { lastSyncTs: null })] });

    expect(card(wrapper, 'DKB').find('[data-testid=bank-balance-card-status]').text()).toBe('FinTS/HBCI');
  });

  it('should show what a bank needs instead of when it synced', () => {
    const wrapper = createWrapper({
      banks: [
        bank('DKB', 0, { authChallenge: { challenge: null, challengeData: null, challengeHtml: null, challengeMimeType: null, primitive: 'otp input', prompt: 'TAN' } }),
        bank('ING', 0, { authExpired: true }),
        bank('Qonto', 0, { lastError: 'boom' }),
      ],
    });

    expect(card(wrapper, 'DKB').find('[data-testid=bank-balance-card-status]').text()).toBe('bank_balances.status.short.authentication');
    expect(card(wrapper, 'ING').find('[data-testid=bank-balance-card-status]').text()).toBe('bank_balances.status.short.expired');
    expect(card(wrapper, 'Qonto').find('[data-testid=bank-balance-card-status]').text()).toBe('bank_balances.status.short.failed');
  });

  it('should spin only the card of a bank being queried', () => {
    const wrapper = createWrapper({ banks: [bank('DKB', 200), bank('ING', 100)], isBankLoading: name => name === 'ING' });

    expect(card(wrapper, 'DKB').find('[data-testid=fiat]').attributes('data-loading')).toBe('false');
    expect(card(wrapper, 'ING').find('[data-testid=fiat]').attributes('data-loading')).toBe('true');
  });
});
