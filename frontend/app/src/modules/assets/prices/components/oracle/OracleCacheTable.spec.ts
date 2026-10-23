import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import OracleCacheTable from '@/modules/assets/prices/components/oracle/OracleCacheTable.vue';
import '@test/i18n';

describe('oracleCacheTable', () => {
  it('should say there are no caches while nothing failed', () => {
    const wrapper = mount(OracleCacheTable, { global: { provide: libraryDefaults }, props: { rows: [] } });

    expect(wrapper.find('[data-testid=oracle-cache-table]').text()).toContain('oracle_prices.cache.dialog.empty');
  });

  it('should name why the caches could not be listed instead', () => {
    const wrapper = mount(OracleCacheTable, { global: { provide: libraryDefaults }, props: { error: new Error('backend down'), rows: [] } });
    const table = wrapper.find('[data-testid=oracle-cache-table]');

    expect(table.text()).toContain('data_table.fetch_failed');
    expect(table.text()).toContain('backend down');
    expect(table.text()).not.toContain('oracle_prices.cache.dialog.empty');
  });
});
