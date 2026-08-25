import type { useAssetDetail } from '@/pages/assets/use-asset-detail';
import { type AssetBalanceWithPrice, bigNumberify } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import AssetLocations from '@/modules/assets/AssetLocations.vue';
import AssetValueRow from '@/modules/assets/AssetValueRow.vue';
import AssetDetailPage from '@/pages/assets/[identifier].vue';

const IDENTIFIER = 'ETH';

const goToEdit = vi.fn();
const toggleIgnoreAsset = vi.fn(async (): Promise<void> => {});
const toggleSpam = vi.fn(async (): Promise<void> => {});
const toggleWhitelistAsset = vi.fn(async (): Promise<void> => {});

interface DetailState {
  collectionBalance: AssetBalanceWithPrice[];
  collectionId: number | undefined;
  isCollectionParent: boolean;
  isCustomAsset: boolean;
  premium: boolean;
}

const detailState = vi.hoisted((): DetailState => ({
  collectionBalance: [],
  collectionId: undefined,
  isCollectionParent: false,
  isCustomAsset: false,
  premium: false,
}));

// `@/modules/premium/premium` reaches the real router through `main.ts`, which blows up under
// vitest. The component itself is stubbed below; this only keeps the import graph out.
vi.mock('@/modules/premium/premium', async () => {
  const { defineComponent } = await import('vue');
  return {
    AssetAmountAndValueOverTime: defineComponent({
      name: 'AssetAmountAndValueOverTime',
      props: { asset: { default: '', type: String }, collectionId: { default: undefined, type: Number }, priceAsset: { default: undefined, type: String } },
      template: '<div />',
    }),
  };
});

vi.mock('@/pages/assets/use-asset-detail', async () => {
  const { computed, shallowRef } = await import('vue');
  return {
    useAssetDetail: (): ReturnType<typeof useAssetDetail> => ({
      asset: computed(() => ({
        assetType: 'evm token',
        coingecko: 'ethereum',
        cryptocompare: 'ETH',
        customAssetType: 'a custom type',
        isCustomAsset: detailState.isCustomAsset,
        name: 'Ethereum',
        resolved: true,
        symbol: 'ETH',
      })),
      collectionAssetWithPrice: computed(() => IDENTIFIER),
      collectionBalance: computed(() => detailState.collectionBalance),
      collectionId: computed(() => detailState.collectionId),
      contractInfo: computed(() => undefined),
      goToEdit,
      isCollectionParent: computed(() => detailState.isCollectionParent),
      isCustomAsset: computed(() => detailState.isCustomAsset),
      loadingIgnore: computed(() => false),
      loadingSpam: computed(() => false),
      loadingWhitelist: computed(() => false),
      premium: shallowRef(detailState.premium),
      toggleIgnoreAsset,
      toggleSpam,
      toggleWhitelistAsset,
    }),
  };
});

/**
 * Declared rather than written inline in `stubs`: an inline stub has no component name, so it can
 * be found neither by name nor with typed `props()`.
 */
const AssetIconStub = defineComponent({
  name: 'AssetIconStub',
  props: { identifier: { default: '', type: String }, showChain: { default: false, type: Boolean }, size: { default: '', type: String } },
  template: '<div />',
});

const AssetBalancesStub = defineComponent({
  name: 'AssetBalancesStub',
  props: { balances: { default: () => [], type: Array }, breakdown: { default: undefined, type: Object } },
  template: '<div data-testid="collection-balances" />',
});

const PremiumChartStub = defineComponent({
  name: 'AssetAmountAndValueOverTime',
  props: { asset: { default: '', type: String }, collectionId: { default: undefined, type: Number }, priceAsset: { default: undefined, type: String } },
  template: '<div />',
});

const IgnoreSwitchStub = defineComponent({
  emits: ['toggle-ignore', 'toggle-whitelist', 'toggle-spam'],
  name: 'IgnoreSwitchStub',
  props: { asset: { default: undefined, type: Object }, loading: { default: false, type: Boolean }, menuLoading: { default: false, type: Boolean } },
  template: '<div data-testid="ignore-switch" />',
});

describe('pages/assets/[identifier]', () => {
  let wrapper: VueWrapper<InstanceType<typeof AssetDetailPage>>;

  function mountPage(): VueWrapper<InstanceType<typeof AssetDetailPage>> {
    return mount(AssetDetailPage, {
      global: {
        plugins: [createPinia()],
        provide: libraryDefaults,
        stubs: {
          AssetAmountAndValueOverTime: PremiumChartStub,
          AssetAmountAndValuePlaceholder: { template: '<div data-testid="chart-placeholder" />' },
          AssetBalances: AssetBalancesStub,
          AssetExternalLinks: { props: ['coingecko', 'cryptocompare'], template: '<div />' },
          AssetIcon: AssetIconStub,
          AssetLocations: { props: ['identifier'], template: '<div data-testid="asset-locations" />' },
          AssetValueRow: { props: ['isCollectionParent', 'identifier'], template: '<div />' },
          HashLink: { props: ['location', 'type', 'text'], template: '<div />' },
          ManagedAssetIgnoreSwitch: IgnoreSwitchStub,
          TablePageLayout: { props: ['hideHeader'], template: '<div><slot /></div>' },
        },
      },
      props: { identifier: IDENTIFIER },
    });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    detailState.collectionBalance = [];
    detailState.collectionId = undefined;
    detailState.isCollectionParent = false;
    detailState.isCustomAsset = false;
    detailState.premium = false;
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should show the symbol above the name for a regular asset', () => {
    wrapper = mountPage();

    expect(wrapper.text()).toContain('ETH');
    expect(wrapper.text()).toContain('Ethereum');
    expect(wrapper.text()).not.toContain('a custom type');
  });

  it('should show the name above the custom type for a custom asset', () => {
    detailState.isCustomAsset = true;

    wrapper = mountPage();

    expect(wrapper.text()).toContain('a custom type');
  });

  it('should hide the ignore switch for a custom asset, which cannot be ignored', () => {
    detailState.isCustomAsset = true;

    wrapper = mountPage();

    expect(wrapper.find('[data-testid=ignore-switch]').exists()).toBe(false);
  });

  it('should forward each switch event to its own action', async () => {
    wrapper = mountPage();
    const ignoreSwitch = wrapper.findComponent(IgnoreSwitchStub);

    ignoreSwitch.vm.$emit('toggle-ignore');
    ignoreSwitch.vm.$emit('toggle-whitelist');
    ignoreSwitch.vm.$emit('toggle-spam');

    expect(toggleIgnoreAsset).toHaveBeenCalledTimes(1);
    expect(toggleWhitelistAsset).toHaveBeenCalledTimes(1);
    expect(toggleSpam).toHaveBeenCalledTimes(1);
  });

  describe('a single asset', () => {
    it('should offer the edit button and run it', async () => {
      wrapper = mountPage();

      await wrapper.find('[data-testid=edit-asset]').trigger('click');

      expect(goToEdit).toHaveBeenCalledTimes(1);
    });

    it('should show the per-location breakdown', () => {
      wrapper = mountPage();

      expect(wrapper.findComponent(AssetLocations).exists()).toBe(true);
      expect(wrapper.find('[data-testid=collection-balances]').exists()).toBe(false);
    });

    it('should show the chain on the icon', () => {
      wrapper = mountPage();

      expect(wrapper.findComponent(AssetIconStub).props('showChain')).toBe(true);
    });
  });

  describe('a collection parent', () => {
    beforeEach(() => {
      detailState.isCollectionParent = true;
    });

    it('should hide the edit button, which has no single asset to edit', () => {
      wrapper = mountPage();

      expect(wrapper.find('[data-testid=edit-asset]').exists()).toBe(false);
    });

    it('should replace the location breakdown with the collection balances', () => {
      detailState.collectionBalance = [{
        amount: bigNumberify(1),
        asset: 'eip155:1/erc20:0xabc',
        price: bigNumberify(2),
        value: bigNumberify(2),
      }];

      wrapper = mountPage();

      expect(wrapper.findComponent(AssetLocations).exists()).toBe(false);
      expect(wrapper.findComponent(AssetBalancesStub).props('balances')).toHaveLength(1);
    });

    it('should not show the chain on the icon', () => {
      wrapper = mountPage();

      expect(wrapper.findComponent(AssetIconStub).props('showChain')).toBe(false);
    });

    it('should tell the value row it is showing a collection', () => {
      wrapper = mountPage();

      expect(wrapper.findComponent(AssetValueRow).props('isCollectionParent')).toBe(true);
    });
  });

  describe('the value-over-time chart', () => {
    it('should show the placeholder without premium', () => {
      wrapper = mountPage();

      expect(wrapper.find('[data-testid=chart-placeholder]').exists()).toBe(true);
      expect(wrapper.findComponent(PremiumChartStub).exists()).toBe(false);
    });

    it('should show the real chart with premium, carrying the priced asset and collection', () => {
      detailState.premium = true;
      detailState.collectionId = 5;

      wrapper = mountPage();

      const chart = wrapper.findComponent(PremiumChartStub);
      expect(chart.exists()).toBe(true);
      expect(chart.props('asset')).toBe(IDENTIFIER);
      expect(chart.props('priceAsset')).toBe(IDENTIFIER);
      expect(chart.props('collectionId')).toBe(5);
    });
  });
});
