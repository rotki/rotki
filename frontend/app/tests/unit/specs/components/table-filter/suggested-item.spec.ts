import type { useAssetIconApi } from '@/composables/api/assets/icon';
import type { Suggestion } from '@/types/filtering';
import SuggestedItem from '@/components/table-filter/SuggestedItem.vue';
import { mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { createCustomPinia } from '../../../utils/create-pinia';

vi.mock('@/composables/assets/retrieval', () => ({
  useAssetInfoRetrieval: vi.fn().mockReturnValue({
    assetInfo: vi.fn().mockImplementation(identifier => ({
      identifier,
      evmChain: 'ethereum',
      symbol: 'SYMBOL 2',
      isCustomAsset: false,
      name: 'Name 2',
    })),
  }),
}));

vi.mock('@/composables/api/assets/icon', () => ({
  useAssetIconApi: vi.fn().mockReturnValue({
    checkAsset: vi.fn().mockResolvedValue(404),
    assetImageUrl: vi.fn(),
  } satisfies Partial<ReturnType<typeof useAssetIconApi>>),
}));

describe('table-filter/SuggestedItem.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof SuggestedItem>>;
  const createWrapper = (props: { suggestion: Suggestion; chip?: boolean }) => {
    const pinia = createCustomPinia();
    setActivePinia(pinia);
    return mount(SuggestedItem, {
      global: {
        plugins: [pinia],
      },
      props: {
        ...props,
      },
    });
  };

  const key = 'start';
  const value = '12/12/2012';
  const assetId = 'asset_id';
  const asset = {
    identifier: assetId,
    evmChain: 'optimism',
    symbol: 'SYMBOL 1',
    isCustomAsset: false,
    name: 'Name 1',
  };

  afterEach(() => {
    wrapper.unmount();
  });

  describe('check if suggestion type is asset', () => {
    it('asset = false', () => {
      const suggestion = {
        index: 0,
        total: 1,
        asset: false,
        key,
        value,
      };
      wrapper = createWrapper({ suggestion });

      expect(wrapper.find('span > span:nth-child(1)').text()).toBe(key);
      expect(wrapper.find('span > span:nth-child(2)').text()).toBe('=');
      expect(wrapper.find('span > span:nth-child(2)').classes().includes('comparator')).toBe(false);
      expect(wrapper.find('span > span:nth-child(3)').text()).toBe(value);
    });

    it('asset = true, send whole asset object', () => {
      const suggestion = {
        index: 0,
        total: 1,
        asset: true,
        key,
        value: asset,
      };
      wrapper = createWrapper({ suggestion });

      expect(wrapper.find('span > span:nth-child(1)').text()).toBe(key);
      expect(wrapper.find('span > div > span').text()).toBe(`${asset.symbol} (${toSentenceCase(asset.evmChain)})`);
    });

    it('asset = true, send only the id', () => {
      const suggestion = {
        index: 0,
        total: 1,
        asset: true,
        key,
        value: assetId,
      };
      wrapper = createWrapper({ suggestion });

      expect(wrapper.find('span > span:nth-child(1)').text()).toBe(key);
      expect(wrapper.find('span > div > span').text()).toBe('SYMBOL 2 (Ethereum)');
    });
  });

  it('exclude = true', () => {
    const suggestion = {
      index: 0,
      total: 1,
      asset: false,
      exclude: true,
      key,
      value,
    };
    wrapper = createWrapper({ suggestion });

    expect(wrapper.find('span > span:nth-child(2)').text()).toBe('!=');
  });

  it('chip = true', () => {
    const suggestion = {
      index: 0,
      total: 1,
      asset: false,
      key,
      value,
    };
    wrapper = createWrapper({ suggestion, chip: true });

    expect(wrapper.find('span > span:nth-child(2)').classes()).toEqual(
      expect.arrayContaining([expect.stringMatching(/_comparator_/)]),
    );
  });

  it('for boolean value', async () => {
    const suggestion = {
      index: 0,
      total: 1,
      asset: false,
      key,
      value: true,
    };
    wrapper = createWrapper({ suggestion });

    expect(wrapper.find('span').text()).toBe(`${key}=true`);

    await wrapper.setProps({ chip: true });

    expect(wrapper.find('span').text()).toBe(key);
  });
});
