import type { ManualPriceWithUsd } from '@/modules/assets/prices/price-types';
import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import LatestPriceContent from '@/modules/assets/prices/latest/LatestPriceContent.vue';
import LatestPriceFormDialog from '@/modules/assets/prices/latest/LatestPriceFormDialog.vue';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

interface Held {
  filter?: Ref<string | undefined>;
  query: Record<string, string>;
}

const { held, spies } = vi.hoisted(() => {
  const held: Held = { query: {} };
  return {
    held,
    spies: {
      deletePrice: vi.fn<(item: { fromAsset: string }) => Promise<void>>(),
      refreshCurrentPrices: vi.fn<() => Promise<void>>(),
      replace: vi.fn<() => Promise<void>>(),
    },
  };
});

vi.mock('vue-router', () => ({
  useRoute: (): Ref<{ query: Record<string, string> }> => ref({ query: held.query }),
  useRouter: (): object => ({ replace: spies.replace }),
}));

const PRICE: ManualPriceWithUsd = {
  fromAsset: 'ETH',
  id: 7,
  price: bigNumberify('1.5'),
  toAsset: 'USD',
  usdPrice: bigNumberify('1.5'),
};

vi.mock('@/modules/assets/prices/use-latest-price-manager', () => ({
  useLatestPrices: (_t: unknown, filter: Ref<string | undefined>): object => {
    held.filter = filter;
    return {
      deletePrice: spies.deletePrice,
      items: computed<ManualPriceWithUsd[]>(() => [PRICE]),
      loading: ref<boolean>(false),
      refreshCurrentPrices: spies.refreshCurrentPrices,
      refreshing: ref<boolean>(false),
    };
  },
}));

describe('latestPriceContent', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof LatestPriceContent>>;

  function createWrapper(): VueWrapper<InstanceType<typeof LatestPriceContent>> {
    return mount(LatestPriceContent, {
      global: {
        plugins: [pinia],
        stubs: {
          AssetSelect: true,
          LatestPriceFormDialog: true,
          RowActions: true,
          RuiDataTable: {
            props: ['rows'],
            template: '<div><div v-for="row in rows" :key="row.id"><slot name="item.actions" :row="row" /></div></div>',
          },
          TablePageLayout: { template: '<div><slot name="buttons" /><slot /></div>' },
        },
      },
    });
  }

  function dialog(): VueWrapper {
    return wrapper.findComponent(LatestPriceFormDialog);
  }

  beforeEach(() => {
    vi.clearAllMocks();
    pinia = createCustomPinia();
    setActivePinia(pinia);
    held.query = {};
    spies.deletePrice.mockResolvedValue(undefined);
    spies.refreshCurrentPrices.mockResolvedValue(undefined);
    spies.replace.mockResolvedValue(undefined);
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should refresh the current prices when it opens', async () => {
    wrapper = createWrapper();
    await flushPromises();

    expect(spies.refreshCurrentPrices).toHaveBeenCalledOnce();
    expect(dialog().props()).toMatchObject({ open: false });
  });

  it('should open an empty form from the add button, even after an edit', async () => {
    wrapper = createWrapper();
    await flushPromises();
    wrapper.findComponent(RowActions).vm.$emit('edit-click');
    await nextTick();

    await wrapper.find('[data-testid=latest-price-add]').trigger('click');

    expect(dialog().props()).toMatchObject({ editableItem: null, open: true });
  });

  it('should open an empty form once when the page is opened to add a price', async () => {
    held.query = { add: 'true' };

    wrapper = createWrapper();
    await flushPromises();

    expect(spies.replace).toHaveBeenCalledExactlyOnceWith({ query: {} });
    expect(dialog().props()).toMatchObject({ editableItem: null, open: true });
  });

  it('should edit a price as form text, without its id or converted price', async () => {
    wrapper = createWrapper();
    await flushPromises();

    wrapper.findComponent(RowActions).vm.$emit('edit-click');
    await nextTick();

    expect(wrapper.findComponent(LatestPriceFormDialog).props('editableItem'))
      .toStrictEqual({ fromAsset: 'ETH', price: '1.5', toAsset: 'USD' });
    expect(dialog().props()).toMatchObject({ open: true });
  });

  it('should delete a price only once the deletion is confirmed', async () => {
    wrapper = createWrapper();
    await flushPromises();

    wrapper.findComponent(RowActions).vm.$emit('delete-click');
    await nextTick();

    expect(useConfirmStore().visible).toBe(true);
    expect(spies.deletePrice).not.toHaveBeenCalled();

    await useConfirmStore().confirm();

    expect(spies.deletePrice).toHaveBeenCalledExactlyOnceWith(PRICE);
  });

  it('should keep the price when the deletion is dismissed', async () => {
    wrapper = createWrapper();
    await flushPromises();

    wrapper.findComponent(RowActions).vm.$emit('delete-click');
    await nextTick();
    await useConfirmStore().dismiss();

    expect(spies.deletePrice).not.toHaveBeenCalled();
  });

  it('should narrow the prices to the asset picked in the filter', async () => {
    wrapper = createWrapper();
    await flushPromises();

    wrapper.findComponent(AssetSelect).vm.$emit('update:modelValue', 'BTC');
    await nextTick();

    expect(get(held.filter)).toBe('BTC');
  });

  it('should refresh the current prices after the form saves', async () => {
    wrapper = createWrapper();
    await flushPromises();
    spies.refreshCurrentPrices.mockClear();

    dialog().vm.$emit('refresh');

    expect(spies.refreshCurrentPrices).toHaveBeenCalledOnce();
  });
});
