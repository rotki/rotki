import {
  type ThisTypedMountOptions,
  type Wrapper,
  mount
} from '@vue/test-utils';
import BigNumber from 'bignumber.js';
import { createPinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import { type Trade } from '@/types/history/trade';
import ExternalTradeForm from '@/components/history/trades/ExternalTradeForm.vue';
import VAutocompleteStub from '../../../stubs/VAutocomplete';
import VComboboxStub from '../../../stubs/VCombobox';

describe('ExternalTradeForm.vue', () => {
  setupDayjs();
  let wrapper: Wrapper<ExternalTradeForm>;

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
    tradeId: '3f6ef0005e6ebf1605a611a02997311595e542c6118726f05f076b89732f0282'
  };

  const createWrapper = (options: ThisTypedMountOptions<any> = {}) => {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(ExternalTradeForm, {
      pinia,
      vuetify,
      stubs: {
        VAutocomplete: VAutocompleteStub,
        VCombobox: VComboboxStub
      },
      ...options
    });
  };

  describe('should prefill the fields based on the props', () => {
    test('no `editableItem` passed', async () => {
      wrapper = createWrapper();
      await wrapper.vm.$nextTick();

      expect(
        (wrapper.find('[data-cy=date] input').element as HTMLInputElement).value
      ).toBeDefined();

      expect(
        (
          wrapper.find('[data-cy=type] [data-cy=trade-input-buy] input')
            .element as HTMLInputElement
        ).value
      ).toBe('buy');

      expect(
        (
          wrapper.find('[data-cy=type] [data-cy=trade-input-sell] input')
            .element as HTMLInputElement
        ).value
      ).toBe('buy');

      expect(
        (wrapper.find('[data-cy=base-asset] input').element as HTMLInputElement)
          .value
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=quote-asset] input')
            .element as HTMLInputElement
        ).value
      ).toBe('');

      expect(
        (wrapper.find('[data-cy=amount] input').element as HTMLInputElement)
          .value
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=trade-rate] [data-cy=primary] input')
            .element as HTMLInputElement
        ).value
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=trade-rate] [data-cy=secondary] input')
            .element as HTMLInputElement
        ).value
      ).toBe('');

      expect(
        (wrapper.find('[data-cy=fee] input').element as HTMLInputElement).value
      ).toBe('');
    });

    test('`editableItem` passed', async () => {
      wrapper = createWrapper({ propsData: { editableItem } });
      await wrapper.vm.$nextTick();

      const buyRadio = wrapper.find(
        '[data-cy=type] [data-cy=trade-input-buy] input'
      );
      const sellRadio = wrapper.find(
        '[data-cy=type] [data-cy=trade-input-sell] input'
      );

      expect((buyRadio.element as HTMLInputElement).value).toBe(
        editableItem.tradeType
      );

      expect((sellRadio.element as HTMLInputElement).value).toBe(
        editableItem.tradeType
      );

      await wrapper
        .find('[data-cy=type] [data-cy=trade-input-sell] input')
        .trigger('click');

      await wrapper.vm.$nextTick();

      expect(
        (wrapper.find('[data-cy=amount] input').element as HTMLInputElement)
          .value
      ).toBe(editableItem.amount.toString());

      expect(
        (
          wrapper.find('[data-cy=trade-rate] [data-cy=primary] input')
            .element as HTMLInputElement
        ).value
      ).toBe(editableItem.rate.toString());

      expect(
        (wrapper.find('[data-cy=fee] input').element as HTMLInputElement).value
      ).toBe(editableItem.fee?.toString());
    });
  });
});
