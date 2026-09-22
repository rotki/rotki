import type { OraclePriceEntry } from '@/modules/assets/prices/price-types';
import type { Collection } from '@/modules/core/common/collection';
import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import OraclePriceContent from '@/modules/assets/prices/components/oracle/OraclePriceContent.vue';
import OraclePriceEditDialog from '@/modules/assets/prices/components/oracle/OraclePriceEditDialog.vue';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import RowActions from '@/modules/shell/components/RowActions.vue';

const { held, spies } = vi.hoisted(() => {
  const held: { rows: OraclePriceEntry[] } = { rows: [] };
  return {
    held,
    spies: {
      deletePrice: vi.fn<(item: OraclePriceEntry) => Promise<boolean>>(),
      refetch: vi.fn<() => Promise<void>>(),
    },
  };
});

vi.mock('@/modules/assets/prices/use-oracle-prices', () => ({
  useOraclePrices: (): object => ({ deletePrice: spies.deletePrice, fetchData: vi.fn() }),
}));

vi.mock('@/modules/core/table/use-server-table', () => ({
  useServerTable: (): object => ({
    collection: ref<Collection<OraclePriceEntry>>({
      data: held.rows,
      found: held.rows.length,
      limit: -1,
      total: held.rows.length,
      totalValue: undefined,
    }),
    error: ref<string>(),
    filter: ref<Record<string, string>>({}),
    isLoading: ref<boolean>(false),
    pagination: ref({ limit: 10, page: 1, total: held.rows.length }),
    refetch: spies.refetch,
  }),
}));

function entry(sourceType: string, fromAsset = 'ETH'): OraclePriceEntry {
  return { fromAsset, price: bigNumberify('2000'), sourceType, timestamp: 1_700_000_000, toAsset: 'USD' };
}

describe('oraclePriceContent', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof OraclePriceContent>>;

  function createWrapper(): VueWrapper<InstanceType<typeof OraclePriceContent>> {
    return mount(OraclePriceContent, {
      global: {
        plugins: [pinia],
        stubs: {
          OraclePriceEditDialog: true,
          PillFilterBar: true,
          RowActions: true,
          RuiChip: true,
          RuiDataTable: {
            props: ['rows'],
            template: `<div>
              <div v-for="row in rows" :key="row.fromAsset">
                <slot name="item.sourceType" :row="row" />
                <slot name="item.actions" :row="row" />
              </div>
            </div>`,
          },
        },
      },
    });
  }

  async function mountWith(rows: OraclePriceEntry[]): Promise<void> {
    held.rows = rows;
    wrapper = createWrapper();
    await flushPromises();
    spies.refetch.mockClear();
  }

  function chip(index: number): Record<string, unknown> {
    return wrapper.findAllComponents({ name: 'RuiChip' })[index].props();
  }

  beforeEach(() => {
    vi.clearAllMocks();
    pinia = createCustomPinia();
    setActivePinia(pinia);
    held.rows = [];
    spies.deletePrice.mockResolvedValue(true);
    spies.refetch.mockResolvedValue(undefined);
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should load the prices when it opens', async () => {
    wrapper = createWrapper();
    await flushPromises();

    expect(spies.refetch).toHaveBeenCalledOnce();
  });

  it('should hand the dialog a copy, so editing leaves the listed price alone', async () => {
    const price = entry(PriceOracle.COINGECKO);
    await mountWith([price]);

    wrapper.findComponent(RowActions).vm.$emit('edit-click');
    await nextTick();

    const editing = wrapper.findComponent(OraclePriceEditDialog).props('modelValue');
    assert(editing);
    expect(editing).toStrictEqual(price);

    editing.toAsset = 'EUR';

    expect(price.toAsset).toBe('USD');
  });

  it('should reload the prices after the dialog saves', async () => {
    await mountWith([entry(PriceOracle.COINGECKO)]);

    wrapper.findComponent(OraclePriceEditDialog).vm.$emit('refresh');

    expect(spies.refetch).toHaveBeenCalledOnce();
  });

  describe('delete', () => {
    it('should delete a price only once confirmed, then reload', async () => {
      const price = entry(PriceOracle.COINGECKO);
      await mountWith([price]);

      wrapper.findComponent(RowActions).vm.$emit('delete-click');
      await nextTick();

      expect(useConfirmStore().visible).toBe(true);
      expect(spies.deletePrice).not.toHaveBeenCalled();

      await useConfirmStore().confirm();

      expect(spies.deletePrice).toHaveBeenCalledExactlyOnceWith(price);
      expect(spies.refetch).toHaveBeenCalledOnce();
    });

    it('should not reload when the price could not be deleted', async () => {
      spies.deletePrice.mockResolvedValue(false);
      await mountWith([entry(PriceOracle.COINGECKO)]);

      wrapper.findComponent(RowActions).vm.$emit('delete-click');
      await nextTick();
      await useConfirmStore().confirm();

      expect(spies.deletePrice).toHaveBeenCalledOnce();
      expect(spies.refetch).not.toHaveBeenCalled();
    });

    it('should keep the price when the deletion is dismissed', async () => {
      await mountWith([entry(PriceOracle.COINGECKO)]);

      wrapper.findComponent(RowActions).vm.$emit('delete-click');
      await nextTick();
      await useConfirmStore().dismiss();

      expect(spies.deletePrice).not.toHaveBeenCalled();
    });
  });

  describe('source chip', () => {
    it('should fill an oracle source with its brand colour', async () => {
      await mountWith([entry(PriceOracle.COINGECKO)]);

      expect(chip(0)).toMatchObject({ bgColor: '#8dc63f', textColor: '#ffffff', variant: 'filled' });
    });

    it('should outline a manual source in the warning colour', async () => {
      await mountWith([entry(PriceOracle.MANUAL)]);

      expect(chip(0)).toMatchObject({ bgColor: undefined, color: 'warning', textColor: undefined, variant: 'outlined' });
    });

    it('should outline a source it has no colour for in grey', async () => {
      await mountWith([entry('some_new_oracle')]);

      expect(chip(0)).toMatchObject({ bgColor: undefined, color: 'grey', variant: 'outlined' });
    });
  });
});
