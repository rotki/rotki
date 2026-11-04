import type { CounterpartyMapping } from '@/modules/assets/admin/counterparty-mapping/schema';
import type { CexMapping } from '@/modules/assets/types';
import type { Collection } from '@/modules/core/common/collection';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import ManageCexMappingTable from '@/modules/assets/admin/cex-mapping/ManageCexMappingTable.vue';
import ManageCounterpartyMappingTable from '@/modules/assets/admin/counterparty-mapping/ManageCounterpartyMappingTable.vue';

vi.mock('@/modules/core/table/pill/composables/use-pill-bar-labels', () => ({
  usePillBarLabels: (): Record<string, unknown> => ({}),
}));

vi.mock('@/modules/core/table/use-table-empty-state', async () => {
  const { computed } = await import('vue');
  return { useTableEmptyState: (): unknown => computed(() => ({})) };
});

/** Renders every column's cell slot per row, so whatever slot name a column key produces is exercised. */
const TableStub = defineComponent({
  emits: ['update:pagination'],
  props: ['cols', 'rows', 'rowAttr', 'loading', 'pagination'],
  template: `<div>
    <div v-for="(row, index) in rows" :key="index" data-testid="row">
      <span v-for="col in cols" :key="col.key" :data-col="col.key"><slot :name="'item.' + col.key" :row="row" /></span>
    </div>
  </div>`,
});

const PillFilterBarStub = defineComponent({
  emits: ['update:matches'],
  props: ['matches', 'fields', 'labels'],
  template: '<div data-testid="pill-filter-bar" />',
});

const stubs = {
  AssetDetails: { props: ['asset'], template: '<span data-testid="asset-details">{{ asset }}</span>' },
  CounterpartyDisplay: { props: ['counterparty'], template: '<span data-testid="counterparty-display">{{ counterparty }}</span>' },
  HintMenuIcon: { template: '<span data-testid="hint"><slot /></span>' },
  LocationDisplay: { props: ['identifier'], template: '<span data-testid="location-display">{{ identifier }}</span>' },
  PillFilterBar: PillFilterBarStub,
  RowActions: {
    emits: ['edit-click', 'delete-click'],
    template: '<span><button data-testid="edit" @click="$emit(\'edit-click\')" /><button data-testid="delete" @click="$emit(\'delete-click\')" /></span>',
  },
  RuiDataTable: TableStub,
  RuiIcon: true,
  TableFrame: { template: '<div><slot name="toolbar" /><slot /></div>' },
};

function collection<T>(data: T[]): Collection<T> {
  return { data, found: data.length, limit: -1, total: data.length, totalValue: undefined };
}

const KRAKEN: CexMapping = { asset: 'BTC', location: 'kraken', locationSymbol: 'XBT' };
const ALL_EXCHANGES: CexMapping = { asset: 'ETH', location: null, locationSymbol: 'ETH2' };
const AAVE: CounterpartyMapping = { asset: 'AAVE', counterparty: 'aave', counterpartySymbol: 'stkAAVE' };

const pagination = { limit: 10, page: 1, total: 0 };

function mountCex(rows: CexMapping[] = [KRAKEN, ALL_EXCHANGES]): VueWrapper<InstanceType<typeof ManageCexMappingTable>> {
  return mount(ManageCexMappingTable, {
    global: { stubs },
    props: { collection: collection(rows), fields: [], filters: {}, loading: false, pagination },
  });
}

function mountCounterparty(): VueWrapper<InstanceType<typeof ManageCounterpartyMappingTable>> {
  return mount(ManageCounterpartyMappingTable, {
    global: { stubs },
    props: { collection: collection([AAVE]), fields: [], filters: {}, loading: false, pagination },
  });
}

function cell(wrapper: VueWrapper, row: number, key: string): ReturnType<VueWrapper['find']> {
  return wrapper.findAll('[data-testid=row]')[row].find(`[data-col=${key}]`);
}

describe('modules/assets/admin/MappingAdminTable', () => {
  describe('with the exchange mapping', () => {
    it('should order the columns source, symbol, asset, actions under the exchange source', () => {
      const table = mountCex().findComponent(TableStub);

      expect(table.props('cols').map((col: { key: string }) => col.key)).toEqual(['location', 'locationSymbol', 'asset', 'actions']);
      expect(table.props('cols')[0].label).toBe('common.exchange');
    });

    it('should key every row uniquely, including several mappings for all exchanges', () => {
      const SECOND_ALL: CexMapping = { asset: 'USDC', location: null, locationSymbol: 'USDC.E' };
      const table = mountCex([KRAKEN, ALL_EXCHANGES, SECOND_ALL]).findComponent(TableStub);
      const rowAttr: string = table.props('rowAttr');
      const keys = table.props('rows').map((row: Record<string, unknown>) => row[rowAttr]);

      expect(new Set(keys).size).toBe(3);
    });

    it('should render the exchange through the source slot', () => {
      const wrapper = mountCex();

      expect(cell(wrapper, 0, 'location').find('[data-testid=location-display]').text()).toBe('kraken');
    });

    it('should say a mapping without an exchange applies to all of them', () => {
      const wrapper = mountCex();
      const source = cell(wrapper, 1, 'location');

      expect(source.find('[data-testid=location-display]').exists()).toBe(false);
      expect(source.text()).toContain('asset_management.cex_mapping.all_exchanges');
    });

    it('should show the exchange subtitle in the toolbar hint', () => {
      expect(mountCex().find('[data-testid=hint]').text()).toBe('asset_management.cex_mapping.subtitle');
    });

    it('should forward edit and delete with the clicked row', async () => {
      const wrapper = mountCex();

      await cell(wrapper, 1, 'actions').find('[data-testid=edit]').trigger('click');
      await cell(wrapper, 0, 'actions').find('[data-testid=delete]').trigger('click');

      expect(wrapper.emitted('edit')).toEqual([[ALL_EXCHANGES]]);
      expect(wrapper.emitted('delete')).toEqual([[KRAKEN]]);
    });

    it('should pass filter changes from the pill bar back up', async () => {
      const wrapper = mountCex();

      wrapper.findComponent(PillFilterBarStub).vm.$emit('update:matches', { location: 'kraken' });
      await nextTick();

      expect(wrapper.emitted('update:filters')).toEqual([[{ location: 'kraken' }]]);
    });

    it('should pass page changes from the table back up', async () => {
      const wrapper = mountCex();
      const next = { limit: 25, page: 2, total: 2 };

      wrapper.findComponent(TableStub).vm.$emit('update:pagination', next);
      await nextTick();

      expect(wrapper.emitted('update:pagination')).toEqual([[next]]);
    });
  });

  describe('with the counterparty mapping', () => {
    it('should lead with the counterparty as the source column', () => {
      const table = mountCounterparty().findComponent(TableStub);

      expect(table.props('cols').map((col: { key: string }) => col.key)).toEqual(['counterparty', 'counterpartySymbol', 'asset', 'actions']);
      expect(table.props('cols')[0].label).toBe('common.counterparty');
    });

    it('should render the counterparty through the source slot', () => {
      const wrapper = mountCounterparty();

      expect(cell(wrapper, 0, 'counterparty').find('[data-testid=counterparty-display]').text()).toBe('aave');
      expect(cell(wrapper, 0, 'asset').find('[data-testid=asset-details]').text()).toBe('AAVE');
    });

    it('should show the counterparty subtitle in the toolbar hint', () => {
      expect(mountCounterparty().find('[data-testid=hint]').text()).toBe('asset_management.counterparty_mapping.subtitle');
    });

    it('should forward edit and delete with the clicked row', async () => {
      const wrapper = mountCounterparty();

      await cell(wrapper, 0, 'actions').find('[data-testid=edit]').trigger('click');
      await cell(wrapper, 0, 'actions').find('[data-testid=delete]').trigger('click');

      expect(wrapper.emitted('edit')).toEqual([[AAVE]]);
      expect(wrapper.emitted('delete')).toEqual([[AAVE]]);
    });

    it('should pass filter and page changes back up', async () => {
      const wrapper = mountCounterparty();
      const next = { limit: 25, page: 2, total: 1 };

      wrapper.findComponent(PillFilterBarStub).vm.$emit('update:matches', { counterparty: 'aave' });
      wrapper.findComponent(TableStub).vm.$emit('update:pagination', next);
      await nextTick();

      expect(wrapper.emitted('update:filters')).toEqual([[{ counterparty: 'aave' }]]);
      expect(wrapper.emitted('update:pagination')).toEqual([[next]]);
    });
  });
});
