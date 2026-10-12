import type { HyperliquidStakingRow } from '@/modules/staking/hyperliquid/use-hyperliquid-staking';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import HyperliquidStakingTable from './HyperliquidStakingTable.vue';

const rows: HyperliquidStakingRow[] = [{
  address: '0xA',
  delegated: bigNumberify(10),
  pendingWithdrawal: bigNumberify(1),
  undelegated: bigNumberify(2),
}];

describe('modules/staking/hyperliquid/HyperliquidStakingTable', () => {
  function mountTable(tableRows: HyperliquidStakingRow[]): VueWrapper {
    return mount(HyperliquidStakingTable, {
      global: {
        stubs: {
          BalanceDisplay: { props: ['value'], template: '<span>{{ value.amount.toString() }}</span>' },
          HashLink: { props: ['text'], template: '<span>{{ text }}</span>' },
          RuiDataTable: {
            props: ['rows', 'cols', 'empty'],
            template: `<div>
              <span v-if="rows.length === 0" data-testid="empty">{{ empty.label }}</span>
              <div v-for="row in rows" :key="row.address">
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

  it('should show each staking state in its own column', () => {
    const wrapper = mountTable(rows);

    expect(['delegated', 'undelegated', 'pendingWithdrawal'].map(key =>
      wrapper.find(`[data-testid=cell-${key}]`).text())).toEqual(['10', '2', '1']);
  });

  it('should show the empty label when nothing is staked', () => {
    const wrapper = mountTable([]);

    expect(wrapper.find('[data-testid=empty]').text()).toBe('staking_page.hyperliquid.table.empty');
  });
});
