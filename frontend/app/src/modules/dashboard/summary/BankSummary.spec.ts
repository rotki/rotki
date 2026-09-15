import type { ExchangeInfo } from '@/modules/balances/types/exchanges';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, ref, type VNode } from 'vue';
import BankSummary from '@/modules/dashboard/summary/BankSummary.vue';
import '@test/i18n';

const mocks = vi.hoisted(() => {
  const banks: { value: unknown[] } = { value: [] };
  return {
    banks,
    refreshBalance: vi.fn<(source: string) => Promise<void>>(),
  };
});

vi.mock('@/modules/balances/use-balance-refresh', () => ({
  useBalanceRefresh: (): Record<string, unknown> => ({ refreshBalance: mocks.refreshBalance }),
}));

vi.mock('@/modules/banks/use-bank-data', () => ({
  useBankData: (): Record<string, unknown> => ({ banks: computed(() => mocks.banks.value) }),
}));

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): Record<string, unknown> => ({ useIsActive: (): unknown => ref(false) }),
}));

const SummaryCardStub = defineComponent({
  name: 'SummaryCard',
  props: { name: { default: '', type: String } },
  emits: ['refresh'],
  setup: (props, { emit, slots }) => (): VNode => h('div', [
    h('button', { 'data-testid': 'summary-refresh', 'onClick': () => emit('refresh', props.name.toLowerCase()) }),
    slots.default?.(),
  ]),
});

describe('bankSummary', () => {
  function createWrapper(): VueWrapper<InstanceType<typeof BankSummary>> {
    return mount(BankSummary, {
      global: {
        stubs: {
          BankBox: { props: ['location', 'amount'], template: '<div data-testid="bank-box">{{ location }} {{ amount }}</div>' },
          SummaryCard: SummaryCardStub,
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

  it('should refresh the bank balances when the card refresh is used', async () => {
    await createWrapper().find('[data-testid=summary-refresh]').trigger('click');
    expect(mocks.refreshBalance).toHaveBeenCalledWith('dashboard.bank_balances.title');
  });
});
