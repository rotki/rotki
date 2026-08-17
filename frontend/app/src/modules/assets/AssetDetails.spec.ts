import type { MaybeRefOrGetter } from 'vue';
import type { AssetActions, AssetDisplay, AssetIdentifierResolution } from '@/modules/assets/types';
import type { AssetResolutionOptions } from '@/modules/assets/use-asset-info-retrieval';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AssetDetails from '@/modules/assets/AssetDetails.vue';

const IDENTIFIER = 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F';

/** The options AssetDetails hands `useAssetInfo`, which is the only thing it computes itself. */
const resolveOptions = vi.fn<(options: AssetResolutionOptions) => void>();

vi.mock('@/modules/assets/use-asset-info-retrieval', async (importOriginal) => {
  const original = await importOriginal<object>();
  return {
    ...original,
    useAssetInfoRetrieval: (): object => ({
      useAssetInfo: (_asset: unknown, options: MaybeRefOrGetter<AssetResolutionOptions>) => computed(() => {
        resolveOptions(toValue(options));
        return { isCustomAsset: false, name: 'Dai Stablecoin', symbol: 'DAI' };
      }),
    }),
  };
});

const AssetDetailsBase = {
  name: 'AssetDetailsBase',
  props: ['asset', 'display', 'actions', 'resolution'],
  template: '<div data-testid="asset-details-base" />',
};

describe('assetDetails', () => {
  interface Props {
    asset?: string;
    display?: AssetDisplay;
    actions?: AssetActions;
    resolution?: AssetIdentifierResolution;
  }

  type AnyProps = ComponentPublicInstance<Record<string, unknown>>;

  function createWrapper(props: Props = {}): VueWrapper {
    return mount(AssetDetails, {
      global: { stubs: { AssetDetailsBase } },
      props: { asset: IDENTIFIER, ...props },
    });
  }

  function base(wrapper: VueWrapper): VueWrapper<AnyProps> {
    return wrapper.findComponent<AnyProps>({ name: 'AssetDetailsBase' });
  }

  beforeEach(() => {
    resolveOptions.mockClear();
  });

  describe('resolution options', () => {
    it('should associate and skip the collection parent by default', () => {
      createWrapper();

      expect(resolveOptions).toHaveBeenLastCalledWith({ associate: true, collectionParent: false });
    });

    it('should stop associating when the resolution bag says so', () => {
      createWrapper({ resolution: { enableAssociation: false } });

      expect(resolveOptions).toHaveBeenLastCalledWith({ associate: false, collectionParent: false });
    });

    it('should resolve the collection parent when asked', () => {
      createWrapper({ resolution: { isCollectionParent: true } });

      expect(resolveOptions).toHaveBeenLastCalledWith({ associate: true, collectionParent: true });
    });

    // `options` is the escape hatch, so it has to win over what the two flags derive. Both
    // NO_COLLECTION_RESOLVE and TradeAssetDisplay rely on that.
    it('should let the options field override the derived flags', () => {
      createWrapper({ resolution: { isCollectionParent: true, options: { collectionParent: false } } });

      expect(resolveOptions).toHaveBeenLastCalledWith({ associate: true, collectionParent: false });
    });
  });

  describe('forwarding', () => {
    it('should hand the resolved asset down under the given identifier', () => {
      const asset = base(createWrapper()).props('asset');

      expect(asset).toStrictEqual({ identifier: IDENTIFIER, isCustomAsset: false, name: 'Dai Stablecoin', symbol: 'DAI' });
    });

    it('should forward the display bag untouched', () => {
      const display: AssetDisplay = { dense: true, iconOnly: true, optimizeForVirtualScroll: true, size: '26px' };

      expect(base(createWrapper({ display })).props('display')).toStrictEqual(display);
    });

    it('should forward the actions bag untouched', () => {
      const actions: AssetActions = { hideActions: true, hideMenu: true };

      expect(base(createWrapper({ actions })).props('actions')).toStrictEqual(actions);
    });

    it('should forward the resolution bag', () => {
      const wrapper = createWrapper({ resolution: { forceChain: 'optimism', isCollectionParent: true } });

      expect(base(wrapper).props('resolution')).toMatchObject({ forceChain: 'optimism', isCollectionParent: true });
    });

    it('should pass no bags on when none were given', () => {
      const wrapper = createWrapper();

      expect(base(wrapper).props('display')).toBeUndefined();
      expect(base(wrapper).props('actions')).toBeUndefined();
    });
  });
});
