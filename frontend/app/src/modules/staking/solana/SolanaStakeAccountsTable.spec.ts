import type { SolanaStakeAccountRow } from '@/modules/staking/solana/use-solana-stake-accounts';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import SolanaStakeAccountsTable from './SolanaStakeAccountsTable.vue';

const rows: SolanaStakeAccountRow[] = [
  { address: 'stake1', amount: bigNumberify(5), owner: 'ownerA', validator: 'vote1' },
  { address: 'stake2', amount: bigNumberify(3), owner: 'ownerA', validator: null },
];

describe('modules/staking/solana/SolanaStakeAccountsTable', () => {
  function mountTable(tableRows: SolanaStakeAccountRow[]): VueWrapper {
    return mount(SolanaStakeAccountsTable, {
      global: {
        stubs: {
          BalanceDisplay: { props: ['value'], template: '<span data-testid="amount">{{ value.amount.toString() }}</span>' },
          HashLink: { props: ['text'], template: '<span data-testid="hash">{{ text }}</span>' },
          RuiDataTable: {
            props: ['rows', 'cols', 'empty'],
            template: `<div>
              <span v-if="rows.length === 0" data-testid="empty">{{ empty.label }}</span>
              <div v-for="row in rows" :key="row.address" :data-testid="'row-' + row.address">
                <div v-for="col in cols" :key="col.key" :data-testid="'cell-' + col.key">
                  <slot :name="'item.' + col.key" :row="row" />
                </div>
              </div>
            </div>`,
          },
        },
      },
      props: { loading: false, rows: tableRows },
    });
  }

  it('should show the amount of each stake account', () => {
    const wrapper = mountTable(rows);

    expect(wrapper.findAll('[data-testid=amount]').map(item => item.text())).toEqual(['5', '3']);
  });

  it('should show the validator of a delegated stake account', () => {
    const wrapper = mountTable(rows);

    expect(wrapper.find('[data-testid=row-stake1] [data-testid=cell-validator]').text()).toBe('vote1');
  });

  it('should mark a stake account without a validator as not delegated', () => {
    const wrapper = mountTable(rows);

    expect(wrapper.find('[data-testid=row-stake2] [data-testid=cell-validator]').text())
      .toBe('staking_page.solana.table.not_delegated');
  });

  it('should show the empty label when there are no stake accounts', () => {
    const wrapper = mountTable([]);

    expect(wrapper.find('[data-testid=empty]').text()).toBe('staking_page.solana.table.empty');
  });
});
