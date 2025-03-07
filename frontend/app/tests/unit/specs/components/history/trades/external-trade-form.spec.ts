import type { useAssetIconApi } from '@/composables/api/assets/icon';
import type { AssetMap } from '@/types/asset';
import ExternalTradeForm from '@/components/history/trades/ExternalTradeForm.vue';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useBalancePricesStore } from '@/store/balances/prices';
import { type Trade, TradeType } from '@/types/history/trade';
import { setupDayjs } from '@/utils/date';
import { createNewTrade } from '@/utils/history/trades';
import { RuiAutoComplete } from '@rotki/ui-library';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import BigNumber from 'bignumber.js';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/store/balances/prices', () => ({
  useBalancePricesStore: vi.fn().mockReturnValue({
    getHistoricPrice: vi.fn(),
  }),
}));

vi.mock('@/composables/api/assets/icon', () => ({
  useAssetIconApi: vi.fn().mockReturnValue({
    checkAsset: vi.fn().mockResolvedValue(404),
  } satisfies Partial<ReturnType<typeof useAssetIconApi>>),
}));

describe('externalTradeForm.vue', () => {
  setupDayjs();
  let wrapper: VueWrapper<InstanceType<typeof ExternalTradeForm>>;
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
    tradeType: TradeType.BUY,
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

  afterEach(() => {
    wrapper.unmount();
  });

  const createWrapper = (options: ComponentMountingOptions<typeof ExternalTradeForm> = {}) =>
    mount(ExternalTradeForm, {
      global: {
        plugins: [pinia],
        components: {
          RuiAutoComplete,
        },
        stubs: {
          Transition: false,
          Teleport: true,
        },
      },
      ...options,
    });

  describe('should prefill the fields based on the props', () => {
    it('empty trade data passed', async () => {
      wrapper = createWrapper({ props: { modelValue: createNewTrade(), editMode: false, errorMessages: {} } });
      await nextTick();

      expect((wrapper.find('[data-cy=date] input').element as HTMLInputElement).value).toBeDefined();
      expect(wrapper.find('[data-cy=type] [data-cy=trade-input-buy] input').attributes()).toHaveProperty('checked');
      expect(wrapper.find('[data-cy=type] [data-cy=trade-input-sell] input').attributes()).not.toHaveProperty(
        'checked',
      );
      expect((wrapper.find('[data-cy=base-asset] input').element as HTMLInputElement).value).toBe('');
      expect((wrapper.find('[data-cy=quote-asset] input').element as HTMLInputElement).value).toBe('');
      expect((wrapper.find('[data-cy=amount] input').element as HTMLInputElement).value).toBe('');
      expect((wrapper.find('[data-cy=trade-rate] [data-cy=primary] input').element as HTMLInputElement).value).toBe('');
      expect((wrapper.find('[data-cy=trade-rate] [data-cy=secondary] input').element as HTMLInputElement).value).toBe(
        '',
      );
      expect((wrapper.find('[data-cy=fee] input').element as HTMLInputElement).value).toBe('');
    });

    it('filled trade data passed', async () => {
      wrapper = createWrapper({ props: { modelValue: editableItem, editMode: true, errorMessages: {} } });
      await nextTick();

      const buyRadio = wrapper.find('[data-cy=type] [data-cy=trade-input-buy] input');
      const sellRadio = wrapper.find('[data-cy=type] [data-cy=trade-input-sell] input');

      const radioAttributes = editableItem.tradeType === TradeType.BUY ? buyRadio.attributes() : sellRadio.attributes();
      expect(radioAttributes).toHaveProperty('checked');

      await wrapper.find('[data-cy=type] [data-cy=trade-input-sell] input').trigger('click');

      await nextTick();

      expect((wrapper.find('[data-cy=amount] input').element as HTMLInputElement).value).toBe(
        editableItem.amount.toString(),
      );
      expect((wrapper.find('[data-cy=trade-rate] [data-cy=primary] input').element as HTMLInputElement).value).toBe(
        editableItem.rate.toString(),
      );
      expect((wrapper.find('[data-cy=fee] input').element as HTMLInputElement).value).toBe(
        editableItem.fee?.toString(),
      );
    });
  });
});
