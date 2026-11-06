import type { OracleCacheMeta } from '@/modules/assets/prices/price-types';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import OracleCacheTable from '@/modules/assets/prices/components/oracle/OracleCacheTable.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';
import '@test/i18n';

type CacheRow = OracleCacheMeta & { id: number };

const ROW: CacheRow = { fromAsset: 'ETH', fromTimestamp: '1', id: 1, toAsset: 'USD', toTimestamp: '2' };

function deleteConfirm(entry: CacheRow): { title: string; message: string } {
  return { message: `Clear ${entry.fromAsset}?`, title: 'Clear cache' };
}

function createWrapper(props: { error?: unknown; rows: CacheRow[] }): VueWrapper<InstanceType<typeof OracleCacheTable>> {
  return mount(OracleCacheTable, {
    global: { provide: libraryDefaults, stubs: { AssetDetails: true, DateDisplay: true, RowActions: true } },
    props: { deleteConfirm, ...props },
  });
}

describe('oracleCacheTable', () => {
  it('should say there are no caches while nothing failed', () => {
    const wrapper = createWrapper({ rows: [] });

    expect(wrapper.find('[data-testid=oracle-cache-table]').text()).toContain('oracle_prices.cache.dialog.empty');
  });

  it('should name why the caches could not be listed instead', () => {
    const wrapper = createWrapper({ error: new Error('backend down'), rows: [] });
    const table = wrapper.find('[data-testid=oracle-cache-table]');

    expect(table.text()).toContain('data_table.fetch_failed');
    expect(table.text()).toContain('backend down');
    expect(table.text()).not.toContain('oracle_prices.cache.dialog.empty');
  });

  it('should have each row ask the question for that row before deleting', () => {
    const wrapper = createWrapper({ rows: [ROW] });

    expect(wrapper.findComponent(RowActions).props('deleteConfirm')).toStrictEqual({ message: 'Clear ETH?', title: 'Clear cache' });
  });

  it('should emit the row the user confirmed deleting', async () => {
    const wrapper = createWrapper({ rows: [ROW] });

    wrapper.findComponent(RowActions).vm.$emit('delete-click');

    expect(wrapper.emitted('delete')).toStrictEqual([[ROW]]);
  });
});
