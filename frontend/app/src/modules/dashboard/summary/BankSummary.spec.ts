import type { ExchangeInfo } from '@/modules/balances/types/exchanges';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import BankSummary from '@/modules/dashboard/summary/BankSummary.vue';
import '@test/i18n';

const mocks = vi.hoisted(() => {
  const banks: { value: unknown[] } = { value: [] };
  return { banks };
});

vi.mock('@/modules/banks/use-bank-data', () => ({
  useBankData: (): Record<string, unknown> => ({ banks: computed(() => mocks.banks.value) }),
}));

describe('bankSummary', () => {
  function createWrapper(): VueWrapper<InstanceType<typeof BankSummary>> {
    return mount(BankSummary, {
      global: {
        stubs: {
          BankBox: { props: ['location', 'amount'], template: '<div data-testid="bank-box">{{ location }} {{ amount }}</div>' },
          SummaryCard: { template: '<div><slot /></div>' },
          SummaryCardCreateButton: { props: ['to'], template: '<a data-testid="create-bank" :data-to="JSON.stringify(to)"><slot /></a>' },
        },
      },
    });
  }

  beforeEach(() => {
    vi.clearAllMocks();
    mocks.banks.value = [];
  });

  it('should offer to add a bank connection when no bank has balances', () => {
    const create = createWrapper().find('[data-testid=create-bank]');
    expect(create.exists()).toBe(true);
    expect(JSON.parse(create.attributes('data-to') ?? '{}')).toEqual({ path: '/api-keys/banks', query: { add: 'true' } });
  });

  it('should list one row per bank with its total', () => {
    mocks.banks.value = [
      { balances: {}, location: 'qonto', total: bigNumberify(250) },
      { balances: {}, location: 'revolut', total: bigNumberify(100) },
    ] satisfies ExchangeInfo[];
    const wrapper = createWrapper();
    expect(wrapper.find('[data-testid=create-bank]').exists()).toBe(false);
    expect(wrapper.findAll('[data-testid=bank-box]').map(box => box.text())).toEqual(['qonto 250', 'revolut 100']);
  });
});
