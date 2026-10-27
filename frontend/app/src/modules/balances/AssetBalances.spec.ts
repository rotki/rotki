import { type AssetBalanceWithPrice, bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import AssetBalances from '@/modules/balances/AssetBalances.vue';
import { provideTableScroller } from '@/modules/core/table/use-table-row-window';

function balance(asset: string): AssetBalanceWithPrice {
  return { amount: bigNumberify(1), asset, price: bigNumberify(2), value: bigNumberify(2) };
}

describe('asset-balances', () => {
  let wrapper: VueWrapper<InstanceType<typeof AssetBalances>>;
  beforeEach(() => {
    const pinia = createCustomPinia();
    setActivePinia(pinia);
    wrapper = mount(AssetBalances, {
      global: {
        plugins: [pinia],
        provide: libraryDefaults,
      },
      props: {
        balances: [],
      },
    });
  });

  afterEach(() => {
    wrapper.unmount();
  });

  it('should enter loading state when balances load', async () => {
    await wrapper.setProps({ loading: true });
    await nextTick();

    expect(wrapper.find('tbody td div[role=progressbar]').exists()).toBe(true);

    await wrapper.setProps({ loading: false });
    await nextTick();

    expect(wrapper.find('tbody td div[role=progressbar]').exists()).toBe(false);
    expect(wrapper.find('tbody tr td p').text()).toMatch('data_table.no_data');
  });

  /** The cells already carry the currency symbol, so the headers never repeat it. */
  it('should leave the currency out of the price and value headers, nested or not', async () => {
    const headers = (): string => wrapper.find('thead').text();

    expect(headers()).not.toContain('_in_symbol');
    expect(headers()).toContain('common.price');
    expect(headers()).toContain('common.value');

    await wrapper.setProps({ layout: 'nested' });

    expect(headers()).not.toContain('_in_symbol');
    expect(headers()).toContain('common.price');
    expect(headers()).toContain('common.value');
  });

  describe('in a panel', () => {
    it('should list every row with no bar and leave the app-wide rows-per-page alone', async () => {
      const itemsPerPage = ref<number>(10);
      const panel = mount(AssetBalances, {
        global: {
          plugins: [createCustomPinia()],
          provide: { [Symbol.for('rui:table').valueOf()]: { globalItemsPerPage: true, itemsPerPage, limits: [10, 25, 50, 100] } },
        },
        props: {
          balances: Array.from({ length: 12 }, (_, index) => balance(`ASSET${index}`)),
          layout: 'panel',
        },
      });
      await nextTick();

      expect(panel.findAll('tbody tr')).toHaveLength(12);
      expect(panel.findComponent({ name: 'RuiTablePagination' }).exists()).toBe(false);
      expect(get(itemsPerPage)).toBe(10);
    });

    it('should drop price and location on a narrow screen so amount and value stay in view', async () => {
      const width = window.innerWidth;
      window.innerWidth = 390;
      window.dispatchEvent(new Event('resize'));
      try {
        const panel = mount(AssetBalances, {
          global: { plugins: [createCustomPinia()], provide: libraryDefaults },
          props: { balances: [balance('ETH')], layout: 'panel', showPerProtocol: true },
        });
        await nextTick();

        const headers = panel.find('thead').text();
        expect(headers).toContain('common.value');
        expect(headers).toContain('common.amount');
        expect(headers).not.toContain('common.price');
        expect(headers).not.toContain('common.location');
      }
      finally {
        window.innerWidth = width;
        window.dispatchEvent(new Event('resize'));
      }
    });
  });
  describe('in a panel under a scroller', () => {
    const balances = Array.from({ length: 100 }, (_, index) => balance(`ASSET${index}`));

    function mountScrolled(selected?: string[]): VueWrapper {
      const Host = defineComponent({
        setup(): () => VNode {
          provideTableScroller(shallowRef<HTMLElement>(document.createElement('div')));
          const model = ref<string[] | undefined>(selected);
          return () => h(AssetBalances, {
            'balances': balances,
            'layout': 'panel',
            'selected': get(model),
            'onUpdate:selected': (value: string[] | undefined) => set(model, value),
          });
        },
      });
      return mount(Host, { global: { plugins: [createCustomPinia()], provide: libraryDefaults } });
    }

    it('should render only part of a long list and stand in for the rest with a spacer', async () => {
      const panel = mountScrolled();
      await nextTick();

      expect(panel.findAll('tbody tr[data-id=row]').length).toBeLessThan(balances.length);
      expect(panel.find('[data-testid=asset-balances-spacer-bottom]').exists()).toBe(true);
    });

    it('should select every row from the select-all checkbox, not only the rendered ones', async () => {
      const panel = mountScrolled([]);
      await nextTick();

      const checkAll = panel.find('thead input[type=checkbox]');
      await checkAll.trigger('click');
      await checkAll.trigger('change');

      const emitted = panel.findComponent(AssetBalances).emitted('update:selected');
      expect(emitted?.at(-1)?.[0]).toHaveLength(balances.length);
    });
  });
});
