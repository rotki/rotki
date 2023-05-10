import { type Wrapper, mount } from '@vue/test-utils';
import Vuetify from 'vuetify';
import SuggestedItem from '@/components/table-filter/SuggestedItem.vue';
import { type Suggestion } from '@/types/filtering';

vi.mock('@/composables/assets/retrieval', () => ({
  useAssetInfoRetrieval: vi.fn().mockReturnValue({
    assetInfo: vi.fn().mockImplementation(identifier => ({
      identifier,
      evmChain: 'ethereum',
      symbol: 'SYMBOL 2',
      isCustomAsset: false,
      name: 'Name 2'
    }))
  })
}));

vi.mocked(useCssModule).mockReturnValue({
  comparator: 'comparator'
});

describe('table-filter/SuggestedItem.vue', () => {
  let wrapper: Wrapper<any>;
  const createWrapper = (props: {
    suggestion?: Suggestion;
    chip?: boolean;
  }) => {
    const vuetify = new Vuetify();
    return mount(SuggestedItem, {
      vuetify,
      propsData: {
        ...props
      }
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
    name: 'Name 1'
  };

  describe('Check if suggestion type is asset', () => {
    it('asset = false', () => {
      const suggestion = {
        index: 0,
        total: 1,
        asset: false,
        key,
        value
      };
      wrapper = createWrapper({ suggestion });

      expect(wrapper.find('span > span:nth-child(1)').text()).toBe(key);
      expect(wrapper.find('span > span:nth-child(2)').text()).toBe('=');
      expect(
        wrapper
          .find('span > span:nth-child(2)')
          .classes()
          .includes('comparator')
      ).toBe(false);
      expect(wrapper.find('span > span:nth-child(3)').text()).toBe(value);
    });

    it('asset = true, send whole asset object', () => {
      const suggestion = {
        index: 0,
        total: 1,
        asset: true,
        key,
        value: asset
      };
      wrapper = createWrapper({ suggestion });

      expect(wrapper.find('span > span:nth-child(1)').text()).toBe(key);
      expect(wrapper.find('span > span:nth-child(3)').text()).toBe(
        `${asset.symbol} (${asset.evmChain})`
      );
    });

    it('asset = true, send only the id', () => {
      const suggestion = {
        index: 0,
        total: 1,
        asset: true,
        key,
        value: assetId
      };
      wrapper = createWrapper({ suggestion });

      expect(wrapper.find('span > span:nth-child(1)').text()).toBe(key);
      expect(wrapper.find('span > span:nth-child(3)').text()).toBe(
        'SYMBOL 2 (ethereum)'
      );
    });
  });

  it('exclude = true', () => {
    const suggestion = {
      index: 0,
      total: 1,
      asset: false,
      exclude: true,
      key,
      value
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
      value
    };
    wrapper = createWrapper({ suggestion, chip: true });

    expect(
      wrapper.find('span > span:nth-child(2)').classes().includes('comparator')
    ).toBe(true);
  });
});
