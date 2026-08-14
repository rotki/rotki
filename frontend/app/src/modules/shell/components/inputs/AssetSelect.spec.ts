import type { AssetSearchSource } from '@/modules/shell/components/inputs/use-asset-search';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';
import '@test/i18n';

/** The options `AssetSelect` hands the search, kept as getters exactly as it passes them. */
type SearchOptions = Record<string, () => unknown>;

const searchOptions = vi.fn<(options: SearchOptions) => void>();

vi.mock('@/modules/shell/components/inputs/use-asset-search', async (importOriginal) => {
  const original = await importOriginal<object>();
  return {
    ...original,
    useAssetSearch: (options: SearchOptions): object => {
      searchOptions(options);
      return {
        error: ref(''),
        getVisibleAsset: (): undefined => undefined,
        loading: ref(false),
        modelSearch: ref(''),
        preload: vi.fn(),
        visibleAssets: computed(() => []),
      };
    },
  };
});

const RuiAutoComplete = {
  name: 'RuiAutoComplete',
  props: ['label', 'options', 'dense', 'hideDetails', 'variant', 'errorMessages'],
  template: '<div class="rui-auto-complete" :data-label="label" :data-variant="variant" />',
};

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
  });

  // Every field of the bag has to reach the search. It is one prop now, so a misspelled key
  // fails silently at runtime rather than at the call site the way five props did.
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

  // The label used to default to a hardcoded English "Asset", which no locale could translate.
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

  it('should draw outlined only when asked', () => {
    const plain = createWrapper();
    expect(plain.get('.rui-auto-complete').attributes('data-variant')).toBe('default');
    plain.unmount();

    const outlined = createWrapper({ outlined: true });
    expect(outlined.get('.rui-auto-complete').attributes('data-variant')).toBe('outlined');
    outlined.unmount();
  });
});
