import { type AssetBalanceWithPrice, bigNumberify, Zero } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type Component, type ComputedRef, defineComponent, h, type VNode } from 'vue';
import DashboardAssetTable from '@/modules/dashboard/DashboardAssetTable.vue';
import { DashboardTableType } from '@/modules/settings/types/frontend-settings';

const pendingAssets = ref<Set<string>>(new Set());

vi.mock('@/modules/assets/prices/use-price-utils', async () => {
  const { computed: createComputed } = await import('vue');
  const { One } = await import('@rotki/common');
  return {
    usePriceUtils: vi.fn(() => ({
      getAssetPrice: (): typeof One => One,
      getAssetPriceOracle: (): string => '',
      getExchangeRate: (): typeof One => One,
      hasCachedPrice: (): boolean => true,
      isManualAssetPrice: (): boolean => false,
      isPricePending: (asset: string): boolean => get(pendingAssets).has(asset),
      useAssetPrice: (): ComputedRef<typeof One> => createComputed(() => One),
      useAssetPriceOracle: (): ComputedRef<string> => createComputed(() => ''),
      useExchangeRate: (): ComputedRef<typeof One> => createComputed(() => One),
      useIsManualAssetPrice: (): ComputedRef<boolean> => createComputed(() => false),
    })),
  };
});

/** Renders only the slots under test, so the assertions do not depend on RuiDataTable internals. */
const RuiDataTableStub = defineComponent({
  props: { rows: { default: () => [], type: Array } },
  setup(props, { slots }): () => VNode {
    return () => h('div', [
      ...props.rows.map(row => h('div', slots['item.value']?.({ row }))),
      h('div', slots['body.append']?.({})),
    ]);
  },
});

function valueStub(testId: string): Component {
  return defineComponent({
    props: {
      asset: { default: '', type: String },
      loading: { default: false, type: Boolean },
      value: { default: undefined, type: Object },
    },
    setup(props): () => VNode {
      return () => h('span', {
        'data-asset': props.asset,
        'data-loading': props.loading ? 'true' : 'false',
        'data-testid': testId,
      });
    },
  });
}

function createBalance(asset: string, overrides: Partial<AssetBalanceWithPrice> = {}): AssetBalanceWithPrice {
  return {
    amount: bigNumberify(3),
    asset,
    price: bigNumberify(2),
    value: bigNumberify(6),
    ...overrides,
  };
}

describe('dashboardAssetTable', () => {
  let wrapper: VueWrapper<InstanceType<typeof DashboardAssetTable>>;

  function createWrapper(balances: AssetBalanceWithPrice[]): VueWrapper<InstanceType<typeof DashboardAssetTable>> {
    return mount(DashboardAssetTable, {
      global: {
        plugins: [createPinia()],
        stubs: {
          AssetValueDisplay: valueStub('row-value'),
          DashboardExpandableTable: { template: '<div><slot /></div>' },
          FiatDisplay: valueStub('total-value'),
          RowAppend: { template: '<div><slot /></div>' },
          RuiDataTable: RuiDataTableStub,
          VisibleColumnsSelector: true,
        },
      },
      props: {
        balances,
        tableType: DashboardTableType.ASSETS,
        title: 'Assets',
      },
    });
  }

  const rowValues = (): Record<string, string> => Object.fromEntries(
    wrapper.findAll('[data-testid=row-value]').map(el => [el.attributes('data-asset') ?? '', el.attributes('data-loading') ?? '']),
  );
  const totalValues = (): string[] => wrapper.findAll('[data-testid=total-value]').map(el => el.attributes('data-loading') ?? '');

  beforeEach(() => {
    setActivePinia(createPinia());
    set(pendingAssets, new Set());
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should show the value once every price is known', () => {
    wrapper = createWrapper([createBalance('ETH'), createBalance('DAI')]);

    expect(rowValues()).toEqual({ DAI: 'false', ETH: 'false' });
    expect(totalValues().every(loading => loading === 'false')).toBe(true);
  });

  it('should load the value of a row whose price has not arrived', () => {
    set(pendingAssets, new Set(['ETH']));
    wrapper = createWrapper([
      createBalance('ETH', { price: bigNumberify(-1), value: Zero }),
      createBalance('DAI'),
    ]);

    expect(rowValues()).toEqual({ DAI: 'false', ETH: 'true' });
  });

  it('should load a group whose member is unpriced, even when the group itself is priced', () => {
    set(pendingAssets, new Set(['USDC_BASE']));
    wrapper = createWrapper([
      createBalance('USDC', { breakdown: [createBalance('USDC'), createBalance('USDC_BASE')] }),
    ]);

    expect(rowValues()).toEqual({ USDC: 'true' });
  });

  it('should load the total while any row is unpriced', () => {
    set(pendingAssets, new Set(['ETH']));
    wrapper = createWrapper([createBalance('ETH'), createBalance('DAI')]);

    expect(totalValues()).toContain('true');
  });
});
