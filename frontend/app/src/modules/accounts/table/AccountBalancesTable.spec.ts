import type { Collection } from '@/modules/core/common/collection';
import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { AccountKind, type BlockchainAccountGroupWithBalance } from '@/modules/accounts/blockchain-accounts';
import AccountBalancesTable from '@/modules/accounts/table/AccountBalancesTable.vue';

vi.mock('@/modules/accounts/table/use-account-loading-states', async () => {
  const { computed } = await import('vue');
  return {
    useAccountLoadingStates: (): object => ({
      accountOperation: computed<boolean>(() => false),
      isInitialLoading: computed<boolean>(() => false),
      isRowLoading: (): boolean => false,
      isSectionLoading: computed<boolean>(() => false),
    }),
  };
});

vi.mock('@/modules/accounts/table/use-account-operations', () => ({
  useAccountOperations: (): object => ({
    confirmDelete: vi.fn<() => void>(),
    deleteAccount: vi.fn<() => Promise<void>>(),
    edit: vi.fn<() => Promise<void>>(),
  }),
}));

vi.mock('@/modules/core/table/use-table-empty-state', async () => {
  const { computed } = await import('vue');
  return {
    useTableEmptyState: (): unknown => computed<object>(() => ({})),
    useTableFetchError: (): undefined => undefined,
  };
});

const stubs = {
  AccountActions: { emits: ['refresh'], name: 'AccountActions', props: ['refreshable'], template: '<div />' },
  AccountBalanceValue: true,
  AccountChains: true,
  AccountTableGroupHeader: true,
  AccountTopTokens: { emits: ['open-details'], name: 'AccountTopTokens', props: ['opensDetails'], template: '<div />' },
  FiatDisplay: true,
  LabeledAddressDisplay: true,
  RowAppend: true,
  RuiDataTable: {
    props: ['rows', 'cols'],
    template: `<div>
      <span v-for="col in cols" :key="col.key" :data-testid="'col-' + col.key" />
      <div v-for="row in rows" :key="row.id" :data-testid="'row-' + row.address">
        <slot name="item.expand" :row="row" />
        <slot name="item.assets" :row="row" />
        <slot name="item.actions" :row="row" />
      </div>
    </div>`,
  },
  TagDisplay: true,
};

function address(id: string, expansion?: 'accounts' | 'assets'): BlockchainAccountGroupWithBalance {
  return {
    address: id,
    category: 'bitcoin',
    chains: ['btc'],
    expansion,
    kind: AccountKind.ADDRESS,
    type: 'group',
    value: bigNumberify(1),
  };
}

function createWrapper(rows: BlockchainAccountGroupWithBalance[], rowRefresh = false): VueWrapper {
  const accounts: Collection<BlockchainAccountGroupWithBalance> = { data: rows, found: rows.length, limit: -1, total: rows.length };
  return mount(AccountBalancesTable, {
    global: { plugins: [createCustomPinia()], stubs },
    props: {
      accounts,
      category: 'bitcoin',
      detailsInDrawer: true,
      group: 'evm',
      pagination: { limit: 10, page: 1, total: rows.length },
      rowRefresh,
      sort: [],
    },
  });
}

describe('modules/accounts/table/AccountBalancesTable', () => {
  it('should offer the details only on a row with something under it', () => {
    const wrapper = createWrapper([address('bc1-tokens', 'assets'), address('bc1-plain')]);

    expect(wrapper.find('[data-testid=row-bc1-tokens] [data-testid=account-open-details]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=row-bc1-plain] [data-testid=account-open-details]').exists()).toBe(false);
  });

  it('should open the details of the row whose button was clicked', async () => {
    const tokens = address('bc1-tokens', 'assets');
    const wrapper = createWrapper([address('bc1-other', 'accounts'), tokens]);

    await wrapper.find('[data-testid=row-bc1-tokens] [data-testid=account-open-details]').trigger('click');

    expect(wrapper.emitted('open-details')).toStrictEqual([[expect.objectContaining({ address: 'bc1-tokens' })]]);
  });

  it('should let the assets count open the details only on a row that has them', async () => {
    const wrapper = createWrapper([address('bc1-tokens', 'assets'), address('bc1-plain')]);
    const withDetails = wrapper.find('[data-testid=row-bc1-tokens]').findComponent({ name: 'AccountTopTokens' });
    const without = wrapper.find('[data-testid=row-bc1-plain]').findComponent({ name: 'AccountTopTokens' });

    expect(withDetails.props('opensDetails')).toBe(true);
    expect(without.props('opensDetails')).toBe(false);

    withDetails.vm.$emit('open-details');
    await nextTick();

    expect(wrapper.emitted('open-details')).toStrictEqual([[expect.objectContaining({ address: 'bc1-tokens' })]]);
  });

  it('should offer each row a refresh only when asked, and pass on the chains it names', async () => {
    expect(createWrapper([address('bc1-plain')]).findComponent({ name: 'AccountActions' }).props('refreshable')).toBe(false);

    const wrapper = createWrapper([address('bc1-plain')], true);
    const actions = wrapper.findComponent({ name: 'AccountActions' });
    expect(actions.props('refreshable')).toBe(true);

    actions.vm.$emit('refresh', ['btc']);
    await nextTick();

    expect(wrapper.emitted('refresh-chains')).toStrictEqual([[['btc']]]);
  });

  it('should keep a lead column while any row has details, so the rows stay aligned', () => {
    expect(createWrapper([address('bc1-tokens', 'assets'), address('bc1-plain')]).find('[data-testid=col-expand]').exists()).toBe(true);
  });

  it('should drop the lead column when no row has anything under it', () => {
    expect(createWrapper([address('bc1-plain'), address('bc1-other')]).find('[data-testid=col-expand]').exists()).toBe(false);
  });
});
