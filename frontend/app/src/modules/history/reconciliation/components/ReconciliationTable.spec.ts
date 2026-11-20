import type { ReconciliationAccount, ReconciliationBucket, StatusCounts } from '@/modules/history/reconciliation/schemas';
import type { AccountDetailState } from '@/modules/history/reconciliation/use-bucket-reconciliation-store';
import { bigNumberify } from '@rotki/common';
import { I18nTStub } from '@test/stubs/I18nT';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import ReconciliationTable from '@/modules/history/reconciliation/components/ReconciliationTable.vue';
import { accountKeyOf } from '@/modules/history/reconciliation/use-reconciliation-rows';
import { createRuiPlugin } from '@/plugins/rui';

vi.mock('@/modules/history/events/mapping/use-history-event-counterparty-mappings', () => ({
  useHistoryEventCounterpartyMappings: (): { getBaseCounterpartyData: () => undefined } => ({
    getBaseCounterpartyData: () => undefined,
  }),
}));

const ReconciliationAmountStub = defineComponent({
  name: 'ReconciliationAmount',
  props: {
    amount: { default: null, type: Object },
    asset: { default: undefined, type: String },
    signed: { default: false, type: Boolean },
  },
  setup(props): () => VNode {
    return (): VNode => {
      const amount = props.amount instanceof Object && 'gt' in props.amount && 'toFixed' in props.amount
        ? props.amount
        : null;
      const sign = props.signed && amount?.gt(0) ? '+' : '';
      const text = amount === null ? 'none' : `${sign}${amount.toFixed()}`;
      return h('span', {
        'data-asset': props.asset,
        'data-signed': String(props.signed),
        'data-testid': 'amount-stub',
      }, text);
    };
  },
});

function counts(overrides: Partial<StatusCounts> = {}): StatusCounts {
  return { blocked: 0, mismatch: 0, notCompared: 0, pending: 0, reconciled: 0, ...overrides };
}

function account(overrides: Partial<ReconciliationAccount> = {}): ReconciliationAccount {
  return {
    counts: counts({ reconciled: 1 }),
    historySyncedTo: 1_700_000_000,
    isExchange: false,
    lastComparedAt: 1_700_000_100,
    lastEventTs: 1_700_000_000_000,
    location: 'ethereum',
    locationLabel: '0x0000000000000000000000000000000000000001',
    ...overrides,
  };
}

function bucket(overrides: Partial<ReconciliationBucket> = {}): ReconciliationBucket {
  return {
    asset: 'eip155:1/erc20:0x0000000000000000000000000000000000000002',
    check: null,
    derivedBalance: null,
    issueId: null,
    issueKind: null,
    lastEventTs: 1_699_000_000_000,
    observedAt: 1_700_000_000,
    observedBalance: null,
    protocol: null,
    reasons: [],
    status: 'reconciled',
    stop: null,
    ...overrides,
  };
}

async function mountExpandedTable(buckets: ReconciliationBucket[]): Promise<VueWrapper> {
  const rowAccount = account();
  const key = accountKeyOf(rowAccount);
  const details: Record<string, AccountDetailState> = {
    [key]: {
      buckets,
      loaded: true,
      loading: false,
      pagination: { limit: 50, offset: 0, total: buckets.length },
      statusKey: '',
    },
  };

  const wrapper = mount(ReconciliationTable, {
    global: {
      plugins: [createPinia(), createRuiPlugin({})],
      stubs: {
        AssetDetails: { props: ['asset'], template: '<span data-testid="asset-stub">{{ asset }}</span>' },
        CounterpartyDisplay: true,
        I18nT: I18nTStub,
        ReconciliationAccountRow: {
          props: ['account'],
          emits: ['toggle'],
          template: '<tr><td colspan="5"><button data-testid="toggle-account" @click="$emit(\'toggle\')">toggle</button></td></tr>',
        },
        ReconciliationAmount: ReconciliationAmountStub,
        ReconciliationStatusCell: {
          props: ['bucket'],
          template: '<span data-testid="status-cell-stub">{{ bucket.status }}</span>',
        },
      },
    },
    props: {
      accounts: [rowAccount],
      details,
      view: 'all',
    },
  });

  await wrapper.get('[data-testid="toggle-account"]').trigger('click');
  return wrapper;
}

describe('reconciliation table', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should display accrued interest subtext under From history for a reconciled accruing bucket', async () => {
    const wrapper = await mountExpandedTable([
      bucket({
        check: {
          accruedInterest: bigNumberify('5'),
          comparedAt: 1_700_000_100,
          delta: bigNumberify('0'),
          derivedBalance: bigNumberify('100'),
          observedAt: 1_700_000_000,
          observedBalance: bigNumberify('105'),
        },
        status: 'reconciled',
      }),
    ]);

    const interest = wrapper.get('[data-testid="reconciliation-accrued-interest"]');
    expect(interest.find('[keypath="data_issues.accrued_interest"]').exists()).toBe(true);
    expect(interest.text()).toContain('+5');
    const interestAmount = interest.get('[data-testid="amount-stub"]');
    expect(interestAmount.attributes('data-signed')).toBe('true');
    expect(interestAmount.attributes('data-asset')).toBeUndefined();

    const amountNodes = wrapper.findAll('[data-testid="amount-stub"]');
    expect(amountNodes.map(node => node.text())).toStrictEqual(['100', '+5', '105']);
    expect(amountNodes.map(node => node.attributes('data-asset'))).toStrictEqual([
      'eip155:1/erc20:0x0000000000000000000000000000000000000002',
      undefined,
      'eip155:1/erc20:0x0000000000000000000000000000000000000002',
    ]);
  });

  it('should show raw From history, accrued interest subtext, and unexplained Difference on mismatch', async () => {
    const wrapper = await mountExpandedTable([
      bucket({
        check: {
          accruedInterest: bigNumberify('5'),
          comparedAt: 1_700_000_100,
          delta: bigNumberify('50'),
          derivedBalance: bigNumberify('100'),
          observedAt: 1_700_000_000,
          observedBalance: bigNumberify('155'),
        },
        status: 'mismatch',
      }),
    ]);

    expect(wrapper.get('[data-testid="reconciliation-accrued-interest"]').text()).toContain('+5');
    const amounts = wrapper.findAll('[data-testid="amount-stub"]').map(node => node.text());
    expect(amounts).toStrictEqual(['100', '+5', '155', '+50']);
  });

  it.each([null, bigNumberify('0')])('should omit accrued interest subtext when adjustment is %s', async (accruedInterest) => {
    const wrapper = await mountExpandedTable([
      bucket({
        check: {
          accruedInterest,
          comparedAt: 1_700_000_100,
          delta: bigNumberify('0'),
          derivedBalance: bigNumberify('100'),
          observedAt: 1_700_000_000,
          observedBalance: bigNumberify('100'),
        },
        status: 'reconciled',
      }),
    ]);

    expect(wrapper.find('[data-testid="reconciliation-accrued-interest"]').exists()).toBe(false);
  });

  it('should omit accrued interest subtext and difference for a pending bucket', async () => {
    const wrapper = await mountExpandedTable([
      bucket({
        derivedBalance: bigNumberify('100'),
        observedBalance: bigNumberify('105'),
        reasons: ['interest_index_missing'],
        status: 'pending',
      }),
    ]);

    expect(wrapper.find('[data-testid="reconciliation-accrued-interest"]').exists()).toBe(false);
    const amounts = wrapper.findAll('[data-testid="amount-stub"]').map(node => node.text());
    expect(amounts).toStrictEqual(['100', '105']);
  });
});
