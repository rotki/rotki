import type { AssetLocation } from '@/modules/assets/use-asset-locations-data';
import { bigNumberify, Blockchain } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, type Ref } from 'vue';
import AssetLocations from '@/modules/assets/AssetLocations.vue';

const { isPricePending, matchChain, visibleAssetLocations } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    isPricePending: vi.fn<(identifier: string) => boolean>(() => false),
    matchChain: vi.fn<(location: string) => string | undefined>(() => undefined),
    visibleAssetLocations: ref<AssetLocation[]>([]),
  };
});

/** Captures the filters the page drives, which is where the exclusivity rule is observable. */
const captured: { addresses?: Ref<string[]>; locationFilter?: Ref<string> } = {};

vi.mock('@/modules/assets/use-asset-locations-data', async () => {
  const { computed } = await import('vue');
  return {
    useAssetLocationsData: (options: {
      addresses: Ref<string[]>;
      locationFilter: Ref<string>;
    }): Record<string, unknown> => {
      captured.addresses = options.addresses;
      captured.locationFilter = options.locationFilter;
      return {
        assetLocations: computed(() => visibleAssetLocations.value),
        currencySymbol: computed(() => 'EUR'),
        detailsLoading: computed(() => false),
        matchChain,
        totalValue: computed(() => visibleAssetLocations.value.reduce(
          (sum, row) => sum.plus(row.value),
          bigNumberify(0),
        )),
        visibleAssetLocations: computed(() => visibleAssetLocations.value),
      };
    },
  };
});

vi.mock('@/modules/assets/prices/use-price-utils', () => ({
  usePriceUtils: (): Record<string, unknown> => ({ isPricePending }),
}));

vi.mock('@/modules/assets/use-asset-location-fields', () => ({
  useAssetLocationFields: (): unknown[] => [],
}));

vi.mock('@/modules/core/table/pill/composables/use-pill-bar-labels', () => ({
  usePillBarLabels: (): Record<string, unknown> => ({}),
}));

vi.mock('@/modules/core/table/use-remember-table-sorting', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/core/table/use-remember-table-sorting')>(),
  useRememberTableSorting: (): void => {},
}));

/** Renders the percentage cell, which is the one the page computes rather than reads. */
const TableStub = defineComponent({
  emits: ['update:pagination', 'update:sort'],
  props: ['cols', 'rows', 'loading', 'sort', 'pagination'],
  template: `<div>
    <template v-for="row in rows" :key="row.label">
      <span class="percentage"><slot name="item.percentage" :row="row" /></span>
    </template>
  </div>`,
});

function location(overrides: Partial<AssetLocation> = {}): AssetLocation {
  return {
    address: '0xaaa',
    amount: bigNumberify(1),
    label: '0xaaa',
    location: Blockchain.ETH,
    value: bigNumberify(100),
    ...overrides,
  };
}

function createWrapper(): VueWrapper<any> {
  return mount(AssetLocations, {
    global: {
      stubs: {
        LabeledAddressDisplay: true,
        LocationDisplay: true,
        PercentageDisplay: { props: ['value'], template: '<span>{{ value }}</span>' },
        PillFilterBar: true,
        RuiCard: { template: '<div><slot name="header" /><slot /></div>' },
        RuiDataTable: TableStub,
        TagDisplay: true,
      },
    },
    props: { identifier: 'ETH' },
  });
}

function table(wrapper: VueWrapper<any>): VueWrapper<any> {
  return wrapper.findComponent(TableStub);
}

function labelOf(wrapper: VueWrapper<any>): string {
  const column = table(wrapper).props('cols').find((col: { key: string }) => col.key === 'label');
  assert(column);
  return column.label;
}

function percentages(wrapper: VueWrapper<any>): string[] {
  return wrapper.findAll('.percentage').map(node => node.text());
}

describe('assetLocations', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    isPricePending.mockReturnValue(false);
    matchChain.mockReturnValue(undefined);
    set(visibleAssetLocations, [location()]);
  });

  /**
   * A validator is not an account, so the column is named for what it actually holds rather than
   * always for one of them.
   */
  describe('the account column', () => {
    it('should be named for accounts when no validator is shown', () => {
      expect(labelOf(createWrapper())).toBe('common.account');
    });

    it('should be named for validators when only validators are shown', () => {
      set(visibleAssetLocations, [location({ location: Blockchain.ETH2 })]);

      expect(labelOf(createWrapper())).toBe('asset_locations.header.validator');
    });

    it('should name both when the rows are mixed', () => {
      set(visibleAssetLocations, [location(), location({ label: 'v1', location: Blockchain.ETH2 })]);

      expect(labelOf(createWrapper())).toBe('common.account / asset_locations.header.validator');
    });
  });

  describe('the share each location holds', () => {
    it('should be the row value against the total', () => {
      set(visibleAssetLocations, [
        location({ value: bigNumberify(25) }),
        location({ label: '0xbbb', value: bigNumberify(75) }),
      ]);

      expect(percentages(createWrapper())).toEqual(['25.00', '75.00']);
    });

    /** Nothing held is not a division to attempt, and every share of it is zero. */
    it('should be zero when nothing is held anywhere', () => {
      set(visibleAssetLocations, [location({ value: bigNumberify(0) })]);

      expect(percentages(createWrapper())).toEqual(['0.00']);
    });
  });

  /**
   * An account is only ever held on a chain, so an exchange location and an account can never both
   * match a row: leaving both set would empty the table.
   */
  describe('keeping the location and account filters exclusive', () => {
    it('should clear the picked accounts when a non-chain location is picked', async () => {
      const wrapper = createWrapper();
      assert(captured.addresses && captured.locationFilter);
      set(captured.addresses, ['0xaaa']);
      await nextTick();

      set(captured.locationFilter, 'kraken');
      await nextTick();

      expect(get(captured.addresses)).toEqual([]);
      expect(wrapper.exists()).toBe(true);
    });

    /** A chain location and an account on that chain agree, so neither has to give way. */
    it('should keep the picked accounts when the location names a chain', async () => {
      matchChain.mockReturnValue(Blockchain.ETH);
      createWrapper();
      assert(captured.addresses && captured.locationFilter);
      set(captured.addresses, ['0xaaa']);
      await nextTick();

      set(captured.locationFilter, Blockchain.ETH);
      await nextTick();

      expect(get(captured.addresses)).toEqual(['0xaaa']);
    });

    it('should clear a non-chain location when accounts are picked', async () => {
      createWrapper();
      assert(captured.addresses && captured.locationFilter);
      set(captured.locationFilter, 'kraken');
      await nextTick();

      set(captured.addresses, ['0xaaa']);
      await nextTick();

      expect(get(captured.locationFilter)).toBe('');
    });
  });

  /** A filter change re-reads the list, so the page it lands on has to start from the first. */
  describe('paging', () => {
    it('should go back to the first page when a filter changes', async () => {
      const wrapper = createWrapper();
      table(wrapper).vm.$emit('update:pagination', { limit: 10, page: 3 });
      await nextTick();

      assert(captured.locationFilter);
      set(captured.locationFilter, 'kraken');
      await nextTick();

      expect(table(wrapper).props('pagination').page).toBe(1);
    });

    it('should follow the table changing page', async () => {
      const wrapper = createWrapper();

      table(wrapper).vm.$emit('update:pagination', { limit: 25, page: 2 });
      await nextTick();

      expect(table(wrapper).props('pagination')).toMatchObject({ limit: 25, page: 2 });
    });

    /** The table reports no pagination while it has none to report, which is not a change. */
    it('should ignore a pagination it was not given', async () => {
      const wrapper = createWrapper();
      const before = table(wrapper).props('pagination');

      table(wrapper).vm.$emit('update:pagination', undefined);
      await nextTick();

      expect(table(wrapper).props('pagination')).toEqual(before);
    });
  });
});
