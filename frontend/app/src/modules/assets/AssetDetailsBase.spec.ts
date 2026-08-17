import type { NftAsset } from '@/modules/assets/nfts';
import type { AssetActions, AssetDisplay, AssetResolution } from '@/modules/assets/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import AssetDetailsBase from '@/modules/assets/AssetDetailsBase.vue';

/**
 * The children are inspected through name selectors, so their instance type is not known here.
 * Declaring the props as an open record is what keeps `props('size')` from narrowing its key to
 * `never`, which a `test:unit` run would not have caught.
 */
type AnyProps = ComponentPublicInstance<Record<string, unknown>>;

type AnyPropsWrapper = VueWrapper<AnyProps>;

const ASSET: NftAsset = {
  identifier: 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F',
  isCustomAsset: false,
  name: 'Dai Stablecoin',
  symbol: 'DAI',
};

const AppImage = {
  name: 'AppImage',
  props: ['src', 'size', 'fit'],
  template: '<img data-testid="app-image" :src="src" />',
};

// `changeable` is declared here although the real AssetIcon has no such prop: that is what lets the
// regression test below see a value if the binding is ever passed again.
const AssetIcon = {
  name: 'AssetIcon',
  props: ['identifier', 'size', 'showChain', 'forceChain', 'resolutionOptions', 'optimizeForVirtualScroll', 'changeable'],
  template: '<div data-testid="asset-icon" />',
};

const AssetDetailsMenuContent = {
  name: 'AssetDetailsMenuContent',
  props: ['asset', 'iconOnly', 'hideActions', 'isCollectionParent'],
  template: '<div data-testid="menu-content" />',
};

// The real menu needs a popper; this keeps the activator slot (and its `attrs`) rendering so the
// icon-only and roomy activator branches can still be told apart.
const RuiMenu = {
  name: 'RuiMenu',
  template: '<div data-testid="rui-menu"><slot name="activator" :attrs="{}" /><slot /></div>',
};

describe('assetDetailsBase', () => {
  interface Props {
    asset?: NftAsset;
    display?: AssetDisplay;
    actions?: AssetActions;
    resolution?: AssetResolution;
  }

  function createWrapper(props: Props = {}): VueWrapper {
    return mount(AssetDetailsBase, {
      global: {
        plugins: [createCustomPinia()],
        stubs: { AppImage, AssetDetailsMenuContent, AssetIcon, RuiMenu },
      },
      props: { asset: ASSET, ...props },
    });
  }

  function icon(wrapper: VueWrapper): AnyPropsWrapper {
    return wrapper.findComponent<AnyProps>({ name: 'AssetIcon' });
  }

  function listItem(wrapper: VueWrapper): AnyPropsWrapper {
    return wrapper.findComponent<AnyProps>({ name: 'ListItem' });
  }

  function menuContent(wrapper: VueWrapper): AnyPropsWrapper {
    return wrapper.findComponent<AnyProps>({ name: 'AssetDetailsMenuContent' });
  }

  function appImage(wrapper: VueWrapper): AnyPropsWrapper {
    return wrapper.findComponent<AnyProps>({ name: 'AppImage' });
  }

  beforeEach(() => {
    setActivePinia(createCustomPinia());
  });

  describe('display defaults', () => {
    it('should fall back to the default size when no display bag is given', () => {
      expect(icon(createWrapper()).props('size')).toBe('30px');
    });

    it('should use the size from the display bag', () => {
      expect(icon(createWrapper({ display: { size: '48px' } })).props('size')).toBe('48px');
    });

    // A caller forwarding its own optional size hands over a present key holding `undefined`.
    // Spreading the bag over a defaults object would take that `undefined` as the value.
    it('should keep the default size when the display bag holds an explicit undefined', () => {
      expect(icon(createWrapper({ display: { size: undefined } })).props('size')).toBe('30px');
    });

    it('should draw a roomy list item by default', () => {
      expect(listItem(createWrapper()).props('size')).toBe('md');
    });

    it('should draw a compact list item when dense', () => {
      expect(listItem(createWrapper({ display: { dense: true } })).props('size')).toBe('sm');
    });

    it('should forward optimizeForVirtualScroll to the icon', () => {
      expect(icon(createWrapper({ display: { optimizeForVirtualScroll: true } })).props('optimizeForVirtualScroll')).toBe(true);
    });
  });

  describe('resolution defaults', () => {
    it('should associate the asset by default', () => {
      expect(icon(createWrapper()).props('resolutionOptions')).toStrictEqual({ associate: true });
    });

    it('should not associate the asset when the resolution bag says so', () => {
      expect(icon(createWrapper({ resolution: { enableAssociation: false } })).props('resolutionOptions')).toStrictEqual({ associate: false });
    });

    // `changeable` was removed from AssetIcon in #7937 (May 2024) when the cache-busting timestamp
    // went away, but two callers kept passing it, so for two years it landed as a DOM attribute and
    // did nothing. Nothing may pass it again: neither as a prop nor as a stray attribute.
    it('should not pass changeable to the icon', () => {
      const wrapper = createWrapper();

      expect(icon(wrapper).props('changeable')).toBeUndefined();
      expect(wrapper.find('[data-testid="asset-icon"]').attributes('changeable')).toBeUndefined();
    });

    // showChain is derived from isCollectionParent rather than being its own prop, so the two can
    // no longer contradict each other. A collection parent stands for several chains.
    it('should show the chain by default', () => {
      expect(icon(createWrapper()).props('showChain')).toBe(true);
    });

    it('should hide the chain for a collection parent', () => {
      expect(icon(createWrapper({ resolution: { isCollectionParent: true } })).props('showChain')).toBe(false);
    });

    it('should forward forceChain to the icon', () => {
      expect(icon(createWrapper({ resolution: { forceChain: 'optimism' } })).props('forceChain')).toBe('optimism');
    });

    it('should tell the menu content whether this is a collection parent', () => {
      const wrapper = createWrapper({ resolution: { isCollectionParent: true } });

      expect(menuContent(wrapper).props('isCollectionParent')).toBe(true);
    });
  });

  describe('actions', () => {
    it('should render the menu by default', () => {
      const wrapper = createWrapper();

      expect(wrapper.find('[data-testid="rui-menu"]').exists()).toBe(true);
      expect(listItem(wrapper).exists()).toBe(true);
    });

    it('should skip the menu entirely when hideMenu is set', () => {
      const wrapper = createWrapper({ actions: { hideMenu: true } });

      expect(wrapper.find('[data-testid="rui-menu"]').exists()).toBe(false);
      expect(listItem(wrapper).exists()).toBe(true);
    });

    it('should render the bare image when hideMenu and iconOnly are both set', () => {
      const wrapper = createWrapper({ actions: { hideMenu: true }, display: { iconOnly: true } });

      expect(wrapper.find('[data-testid="rui-menu"]').exists()).toBe(false);
      expect(listItem(wrapper).exists()).toBe(false);
      expect(icon(wrapper).exists()).toBe(true);
    });

    it('should forward hideActions to the menu content', () => {
      const wrapper = createWrapper({ actions: { hideActions: true } });

      expect(menuContent(wrapper).props('hideActions')).toBe(true);
    });

    it('should not hide the menu actions by default', () => {
      expect(menuContent(createWrapper()).props('hideActions')).toBe(false);
    });
  });

  describe('image source', () => {
    it('should draw the asset icon when the asset has no image url', () => {
      const wrapper = createWrapper();

      expect(icon(wrapper).exists()).toBe(true);
      expect(wrapper.find('[data-testid="app-image"]').exists()).toBe(false);
    });

    it('should draw the image url when the asset has one', () => {
      const wrapper = createWrapper({ asset: { ...ASSET, imageUrl: 'https://example.com/dai.png' } });

      expect(wrapper.find('[data-testid="app-image"]').attributes('src')).toBe('https://example.com/dai.png');
      expect(icon(wrapper).exists()).toBe(false);
    });

    it('should size the image url with the same display size', () => {
      const wrapper = createWrapper({ asset: { ...ASSET, imageUrl: 'https://example.com/dai.png' }, display: { size: '48px' } });

      expect(appImage(wrapper).props('size')).toBe('48px');
    });
  });
});
