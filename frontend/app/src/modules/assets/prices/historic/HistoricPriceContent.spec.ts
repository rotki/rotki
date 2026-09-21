import type { HistoricalPrice } from '@/modules/assets/prices/price-types';
import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import HistoricPriceContent from '@/modules/assets/prices/historic/HistoricPriceContent.vue';
import HistoricPriceFormDialog from '@/modules/assets/prices/historic/HistoricPriceFormDialog.vue';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import RowActions from '@/modules/shell/components/RowActions.vue';

interface PriceFilter {
  fromAsset?: string;
  toAsset?: string;
}

interface Held {
  filter?: Ref<PriceFilter>;
  query: Record<string, string>;
}

const { held, spies } = vi.hoisted(() => {
  const held: Held = { query: {} };
  return {
    held,
    spies: {
      deletePrice: vi.fn<(item: HistoricalPrice) => Promise<void>>(),
      refresh: vi.fn<(payload?: { modified: boolean }) => Promise<void>>(),
      replace: vi.fn<() => Promise<void>>(),
    },
  };
});

vi.mock('vue-router', () => ({
  useRoute: (): Ref<{ query: Record<string, string> }> => ref({ query: held.query }),
  useRouter: (): object => ({ replace: spies.replace }),
}));

const PRICE: HistoricalPrice = {
  fromAsset: 'ETH',
  price: bigNumberify('1850.25'),
  timestamp: 1_700_000_000,
  toAsset: 'EUR',
};

vi.mock('@/modules/assets/prices/use-historic-price-manager', () => ({
  useHistoricPrices: (_t: unknown, filter: Ref<PriceFilter>): object => {
    held.filter = filter;
    return {
      deletePrice: spies.deletePrice,
      items: ref<HistoricalPrice[]>([PRICE]),
      loading: ref<boolean>(false),
      refresh: spies.refresh,
    };
  },
}));

const NOW = 1_750_000_000;

describe('historicPriceContent', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof HistoricPriceContent>>;

  function createWrapper(): VueWrapper<InstanceType<typeof HistoricPriceContent>> {
    return mount(HistoricPriceContent, {
      global: {
        plugins: [pinia],
        stubs: {
          HistoricPriceFormDialog: true,
          PillFilterBar: true,
          RowActions: true,
          RuiDataTable: {
            props: ['rows'],
            template: '<div><div v-for="row in rows" :key="row.fromAsset"><slot name="item.actions" :row="row" /></div></div>',
          },
          TablePageLayout: { template: '<div><slot name="buttons" /><slot /></div>' },
        },
      },
    });
  }

  async function filterBy(matches: Record<string, unknown>): Promise<void> {
    wrapper.findComponent(PillFilterBar).vm.$emit('update:matches', matches);
    await nextTick();
  }

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(NOW * 1000);
    pinia = createCustomPinia();
    setActivePinia(pinia);
    held.query = {};
    spies.deletePrice.mockResolvedValue(undefined);
    spies.refresh.mockResolvedValue(undefined);
    spies.replace.mockResolvedValue(undefined);
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  describe('filter', () => {
    it('should narrow the prices to the pair picked in the filter bar', async () => {
      wrapper = createWrapper();

      await filterBy({ fromAsset: 'ETH', toAsset: 'EUR' });

      expect(get(held.filter)).toEqual({ fromAsset: 'ETH', toAsset: 'EUR' });
    });

    it('should ignore a pill that has no value yet', async () => {
      wrapper = createWrapper();

      await filterBy({ fromAsset: '', toAsset: ['EUR'] });

      expect(get(held.filter)).toEqual({ fromAsset: undefined, toAsset: undefined });
    });
  });

  describe('add', () => {
    it('should open an empty manual price for the current time', async () => {
      wrapper = createWrapper();

      await wrapper.find('[data-testid=historic-price-add]').trigger('click');

      const dialog = wrapper.findComponent(HistoricPriceFormDialog);
      expect(dialog.props('modelValue')).toStrictEqual({
        fromAsset: '',
        price: '',
        sourceType: PriceOracle.MANUAL,
        timestamp: NOW,
        toAsset: '',
      });
      expect(dialog.props('editMode')).toBe(false);
    });

    it('should start the new price from the filtered pair', async () => {
      wrapper = createWrapper();
      await filterBy({ fromAsset: 'BTC', toAsset: 'USD' });

      await wrapper.find('[data-testid=historic-price-add]').trigger('click');

      expect(wrapper.findComponent(HistoricPriceFormDialog).props('modelValue'))
        .toMatchObject({ fromAsset: 'BTC', toAsset: 'USD' });
    });

    it('should leave edit mode when adding after an edit', async () => {
      wrapper = createWrapper();
      wrapper.findComponent(RowActions).vm.$emit('edit-click');
      await nextTick();

      await wrapper.find('[data-testid=historic-price-add]').trigger('click');

      expect(wrapper.findComponent(HistoricPriceFormDialog).props('editMode')).toBe(false);
    });

    it('should open the form once when the page is opened to add a price', async () => {
      held.query = { add: 'true' };

      wrapper = createWrapper();
      await flushPromises();

      expect(spies.replace).toHaveBeenCalledExactlyOnceWith({ query: {} });
      expect(wrapper.findComponent(HistoricPriceFormDialog).props('modelValue')).toMatchObject({ timestamp: NOW });
    });
  });

  it('should edit a price as form text, recorded as a manual price', async () => {
    wrapper = createWrapper();

    wrapper.findComponent(RowActions).vm.$emit('edit-click');
    await nextTick();

    const dialog = wrapper.findComponent(HistoricPriceFormDialog);
    expect(dialog.props('modelValue')).toStrictEqual({
      fromAsset: 'ETH',
      price: '1850.25',
      sourceType: PriceOracle.MANUAL,
      timestamp: 1_700_000_000,
      toAsset: 'EUR',
    });
    expect(dialog.props('editMode')).toBe(true);
  });

  describe('delete', () => {
    it('should delete a price only once the deletion is confirmed', async () => {
      wrapper = createWrapper();

      wrapper.findComponent(RowActions).vm.$emit('delete-click');
      await nextTick();

      expect(useConfirmStore().visible).toBe(true);
      expect(spies.deletePrice).not.toHaveBeenCalled();

      await useConfirmStore().confirm();

      expect(spies.deletePrice).toHaveBeenCalledExactlyOnceWith(PRICE);
    });

    it('should keep the price when the deletion is dismissed', async () => {
      wrapper = createWrapper();

      wrapper.findComponent(RowActions).vm.$emit('delete-click');
      await nextTick();
      await useConfirmStore().dismiss();

      expect(spies.deletePrice).not.toHaveBeenCalled();
    });
  });

  it('should reload the prices as modified after the form saves', async () => {
    wrapper = createWrapper();

    wrapper.findComponent(HistoricPriceFormDialog).vm.$emit('refresh');

    expect(spies.refresh).toHaveBeenCalledExactlyOnceWith({ modified: true });
  });
});
