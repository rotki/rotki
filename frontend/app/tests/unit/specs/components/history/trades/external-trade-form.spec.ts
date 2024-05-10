import {
  type ThisTypedMountOptions,
  type Wrapper,
  mount,
} from '@vue/test-utils';
import BigNumber from 'bignumber.js';
import { type Pinia, createPinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import ExternalTradeForm from '@/components/history/trades/ExternalTradeForm.vue';
import type { AssetMap } from '@/types/asset';
import type { Trade } from '@/types/history/trade';

vi.mock('@/store/balances/prices', () => ({
  useBalancePricesStore: vi.fn().mockReturnValue({
    getHistoricPrice: vi.fn(),
  }),
}));

describe('externalTradeForm.vue', () => {
  setupDayjs();
  let wrapper: Wrapper<ExternalTradeForm>;
  let pinia: Pinia;

  const baseAsset = {
    name: 'USDT Stablecoin',
    symbol: 'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7',
    assetType: 'own chain',
    isCustomAsset: false,
  };

  const quoteAsset = {
    name: 'United States Dollar',
    symbol: 'USD',
    assetType: 'fiat',
    isCustomAsset: false,
  };

  const mapping: AssetMap = {
    assetCollections: {},
    assets: { [baseAsset.symbol]: baseAsset, [quoteAsset.symbol]: quoteAsset },
  };

  const editableItem: Trade = {
    timestamp: 1701252793,
    location: 'binance',
    baseAsset: 'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7',
    quoteAsset: 'USD',
    tradeType: 'buy',
    amount: BigNumber('164.02653038'),
    rate: BigNumber('1.0455016'),
    fee: BigNumber('3.51'),
    feeCurrency: 'USD',
    link: 'N01426305048994642944112998',
    notes: null,
    tradeId: '3f6ef0005e6ebf1605a611a02997311595e542c6118726f05f076b89732f0282',
  };

  beforeEach(() => {
    vi.useFakeTimers();
    pinia = createPinia();
    setActivePinia(pinia);
    vi.mocked(useAssetInfoApi().assetMapping).mockResolvedValue(mapping);
    vi.mocked(useBalancePricesStore().getHistoricPrice).mockResolvedValue(One);
  });

  const createWrapper = (options: ThisTypedMountOptions<any> = {}) => {
    const vuetify = new Vuetify();
    return mount(ExternalTradeForm, {
      pinia,
      vuetify,
      ...options,
    });
  };

  describe('should prefill the fields based on the props', () => {
    it('no `editableItem` passed', async () => {
      wrapper = createWrapper();
      await nextTick();

      expect(
        (wrapper.find('[data-cy=date] input').element as HTMLInputElement).value,
      ).toBeDefined();

      expect(
        (
          wrapper.find('[data-cy=type] [data-cy=trade-input-buy] input')
            .element as HTMLInputElement
        ).value,
      ).toBe('buy');

      expect(
        (
          wrapper.find('[data-cy=type] [data-cy=trade-input-sell] input')
            .element as HTMLInputElement
        ).value,
      ).toBe('buy');

      expect(
        (wrapper.find('[data-cy=base-asset] input').element as HTMLInputElement)
          .value,
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=quote-asset] input')
            .element as HTMLInputElement
        ).value,
      ).toBe('');

      expect(
        (wrapper.find('[data-cy=amount] input').element as HTMLInputElement)
          .value,
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=trade-rate] [data-cy=primary] input')
            .element as HTMLInputElement
        ).value,
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=trade-rate] [data-cy=secondary] input')
            .element as HTMLInputElement
        ).value,
      ).toBe('');

      expect(
        (wrapper.find('[data-cy=fee] input').element as HTMLInputElement).value,
      ).toBe('');
    });

    it('`editableItem` passed', async () => {
      wrapper = createWrapper();
      await nextTick();
      await wrapper.setProps({ editableItem });

      const buyRadio = wrapper.find(
        '[data-cy=type] [data-cy=trade-input-buy] input',
      );
      const sellRadio = wrapper.find(
        '[data-cy=type] [data-cy=trade-input-sell] input',
      );

      expect((buyRadio.element as HTMLInputElement).value).toBe(
        editableItem.tradeType,
      );

      expect((sellRadio.element as HTMLInputElement).value).toBe(
        editableItem.tradeType,
      );

      await wrapper
        .find('[data-cy=type] [data-cy=trade-input-sell] input')
        .trigger('click');

      await nextTick();

      expect(
        (wrapper.find('[data-cy=amount] input').element as HTMLInputElement)
          .value,
      ).toBe(editableItem.amount.toString());

      expect(
        (
          wrapper.find('[data-cy=trade-rate] [data-cy=primary] input')
            .element as HTMLInputElement
        ).value,
      ).toBe(editableItem.rate.toString());

      expect(
        (wrapper.find('[data-cy=fee] input').element as HTMLInputElement).value,
      ).toBe(editableItem.fee?.toString());
    });
  });
});
