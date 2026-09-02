import type { AssetSearchSource } from '@/modules/shell/components/inputs/use-asset-search';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AssetDetailsBase from '@/modules/assets/AssetDetailsBase.vue';
import AssetIcon from '@/modules/shell/components/AssetIcon.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';
import '@test/i18n';

/** The options `AssetSelect` hands the search, kept as getters exactly as it passes them. */
type SearchOptions = Record<string, () => unknown>;

const searchOptions = vi.fn<(options: SearchOptions) => void>();

const { visibleAssets } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { visibleAssets: ref<{ assetType?: string; identifier: string; symbol?: string }[]>([]) };
});

vi.mock('@/modules/shell/components/inputs/use-asset-search', async (importOriginal) => {
  const original = await importOriginal<object>();
  const { ref: vueRef } = await import('vue');
  return {
    ...original,
    useAssetSearch: (options: SearchOptions): object => {
      searchOptions(options);
      return {
        error: vueRef(''),
        getVisibleAsset: (): undefined => undefined,
        loading: vueRef(false),
        modelSearch: vueRef(''),
        preload: vi.fn(),
        visibleAssets,
      };
    },
  };
});

/**
 * Mirrors `RuiAutoComplete`'s slot contract: `selection` renders the option matching the model,
 * `item` renders once per option, and `no-data` stands in for an empty list.
 *
 * @remarks
 * Keyed by `identifier`, matching the `key-attr` the component passes. A stub that renders no
 * slots makes every assertion about the rendered asset pass whether or not it renders.
 */
const RuiAutoComplete = defineComponent({
  name: 'RuiAutoComplete',
  props: {
    dense: { default: false, type: Boolean },
    errorMessages: { default: undefined, type: [String, Array] },
    hideDetails: { default: false, type: Boolean },
    label: { default: undefined, type: String },
    modelValue: { default: undefined, type: String },
    options: { default: () => [], type: Array },
    variant: { default: undefined, type: String },
  },
  template: `<div
    class="rui-auto-complete"
    :data-label="label"
    :data-variant="variant"
    :data-dense="String(dense === true)"
    :data-hide-details="String(hideDetails === true)"
  >
    <template v-for="option in options" :key="option.identifier">
      <div v-if="option.identifier === modelValue" class="selection">
        <slot name="selection" :item="option" />
      </div>
    </template>
    <div class="menu">
      <slot v-if="options.length === 0" name="no-data" />
      <div v-for="option in options" :key="option.identifier" class="option">
        <slot name="item" :item="option" />
      </div>
    </div>
  </div>`,
});

function createWrapper(props: Record<string, unknown> = {}): VueWrapper {
  return mount(AssetSelect, {
    global: {
      stubs: {
        AssetDetailsBase: true,
        AssetIcon: true,
        NftDetails: true,
        RuiAutoComplete,
      },
    },
    props: { modelValue: undefined, ...props },
  });
}

/** The last `useAssetSearch` options, with its getters resolved to plain values. */
function lastSource(): Record<string, unknown> {
  const options = searchOptions.mock.lastCall?.[0] ?? {};
  return {
    chain: options.chain(),
    excludes: options.excludes(),
    items: options.items(),
    nftHandling: options.nftHandling(),
    showIgnored: options.showIgnored(),
  };
}

describe('assetSelect', () => {
  beforeEach(() => {
    searchOptions.mockClear();
    set(visibleAssets, []);
  });

  it('should pass every field of the source bag to the search', () => {
    const source: AssetSearchSource = {
      chain: 'eth',
      excludes: ['BTC'],
      items: ['ETH'],
      nfts: 'show_only',
      showIgnored: true,
    };

    const wrapper = createWrapper({ source });

    expect(lastSource()).toStrictEqual({
      chain: 'eth',
      excludes: ['BTC'],
      items: ['ETH'],
      nftHandling: 'show_only',
      showIgnored: true,
    });

    wrapper.unmount();
  });

  it('should leave nfts out and show no ignored assets when no source is given', () => {
    const wrapper = createWrapper();

    expect(lastSource()).toStrictEqual({
      chain: undefined,
      excludes: [],
      items: [],
      nftHandling: 'exclude',
      showIgnored: false,
    });

    wrapper.unmount();
  });

  it('should fall back to the translated label', () => {
    const wrapper = createWrapper();

    expect(wrapper.get('.rui-auto-complete').attributes('data-label')).toBe('asset_select.label');

    wrapper.unmount();
  });

  it('should keep a label the caller gives it', () => {
    const wrapper = createWrapper({ label: 'Fee asset' });

    expect(wrapper.get('.rui-auto-complete').attributes('data-label')).toBe('Fee asset');

    wrapper.unmount();
  });

  it('should pass each of the three variants through, defaulting to the plain one', () => {
    const plain = createWrapper();
    expect(plain.get('.rui-auto-complete').attributes('data-variant')).toBe('default');
    plain.unmount();

    for (const variant of ['outlined', 'filled'] as const) {
      const wrapper = createWrapper({ variant });
      expect(wrapper.get('.rui-auto-complete').attributes('data-variant')).toBe(variant);
      wrapper.unmount();
    }
  });

  it('should render the selected asset in the field and every option in the menu', () => {
    set(visibleAssets, [{ identifier: 'ETH', symbol: 'ETH' }, { identifier: 'DAI', symbol: 'DAI' }]);
    const wrapper = createWrapper({ modelValue: 'ETH' });

    expect(wrapper.find('.selection').findComponent(AssetDetailsBase).exists()).toBe(true);
    expect(wrapper.findAll('.option')).toHaveLength(2);

    wrapper.unmount();
  });

  it('should draw a dense selection without AssetDetailsBase, whose stacked lines grow the field back', () => {
    set(visibleAssets, [{ identifier: 'ETH', symbol: 'ETH' }]);

    const dense = createWrapper({ dense: true, modelValue: 'ETH' });
    expect(dense.get('.rui-auto-complete').attributes('data-dense')).toBe('true');
    expect(dense.find('.selection').findComponent(AssetDetailsBase).exists()).toBe(false);
    expect(dense.find('.selection').findComponent(AssetIcon).props('size')).toBe('20px');
    dense.unmount();

    const roomy = createWrapper({ modelValue: 'ETH' });
    expect(roomy.find('.selection').findComponent(AssetDetailsBase).exists()).toBe(true);
    roomy.unmount();
  });
});
