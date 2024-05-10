import {
  type ThisTypedMountOptions,
  type Wrapper,
  mount,
} from '@vue/test-utils';
import { type Pinia, createPinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import EthDepositEventForm from '@/components/history/events/forms/EthDepositEventForm.vue';
import type { AssetMap } from '@/types/asset';
import type { EthDepositEvent } from '@/types/history/events';

vi.mock('json-editor-vue', () => ({
  template: '<input />',
}));

vi.mock('@/store/balances/prices', () => ({
  useBalancePricesStore: vi.fn().mockReturnValue({
    getHistoricPrice: vi.fn(),
  }),
}));

describe('ethDepositEventForm.vue', () => {
  setupDayjs();
  let wrapper: Wrapper<EthDepositEventForm>;
  let pinia: Pinia;

  const asset = {
    name: 'Ethereum',
    symbol: 'ETH',
    assetType: 'own chain',
    isCustomAsset: false,
  };

  const mapping: AssetMap = {
    assetCollections: {},
    assets: { [asset.symbol]: asset },
  };

  const groupHeader: EthDepositEvent = {
    identifier: 11344,
    entryType: HistoryEventEntryType.ETH_DEPOSIT_EVENT,
    eventIdentifier:
      '10x3849ac4b278cac18f0e52a7d1a1dc1c14b1b4f50d6c11087e9a6591fd7b62d08',
    sequenceIndex: 12,
    timestamp: 1697522243000,
    location: 'ethereum',
    asset: asset.symbol,
    balance: {
      amount: bigNumberify('3.2'),
      usdValue: bigNumberify('5082.048'),
    },
    eventType: 'staking',
    eventSubtype: 'deposit asset',
    locationLabel: '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
    notes: 'Deposit 3.2 ETH to validator 223',
    txHash:
      '0x3849ac4b278cac18f0e52a7d1a1dc1c14b1b4f50d6c11087e9a6591fd7b62d08',
    counterparty: 'eth2',
    product: 'staking',
    address: '0x00000000219ab540356cBB839Cbe05303d7705Fa',
    validatorIndex: 223,
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
    return mount(EthDepositEventForm, {
      pinia,
      vuetify,
      ...options,
    });
  };

  describe('should prefill the fields based on the props', () => {
    it('no `groupHeader`, `editableItem`, nor `nextSequence` are passed', async () => {
      wrapper = createWrapper();
      await nextTick();

      await wrapper
        .find('[data-cy=eth-deposit-event-form__advance] .accordion__header')
        .trigger('click');
      await nextTick();

      expect(
        (
          wrapper.find('[data-cy=validatorIndex] input')
            .element as HTMLInputElement
        ).value,
      ).toBe('');

      expect(
        (wrapper.find('[data-cy=txHash] input').element as HTMLInputElement)
          .value,
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=eventIdentifier] input')
            .element as HTMLInputElement
        ).value,
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=depositor] .input-value')
            .element as HTMLInputElement
        ).value,
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=sequenceIndex] input')
            .element as HTMLInputElement
        ).value,
      ).toBe('');
    });

    it('`groupHeader` and `nextSequence` are passed', async () => {
      wrapper = createWrapper();
      await nextTick();
      await wrapper.setProps({ groupHeader, nextSequence: '10' });

      await wrapper
        .find('[data-cy=eth-deposit-event-form__advance] .accordion__header')
        .trigger('click');
      await nextTick();

      expect(
        (
          wrapper.find('[data-cy=validatorIndex] input')
            .element as HTMLInputElement
        ).value,
      ).toBe(groupHeader.validatorIndex.toString());

      expect(
        (wrapper.find('[data-cy=txHash] input').element as HTMLInputElement)
          .value,
      ).toBe(groupHeader.txHash);

      expect(
        (
          wrapper.find('[data-cy=eventIdentifier] input')
            .element as HTMLInputElement
        ).value,
      ).toBe(groupHeader.eventIdentifier);

      expect(
        (
          wrapper.find('[data-cy=depositor] .input-value')
            .element as HTMLInputElement
        ).value,
      ).toBe(groupHeader.locationLabel);

      expect(
        (wrapper.find('[data-cy=amount] input').element as HTMLInputElement)
          .value,
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=sequenceIndex] input')
            .element as HTMLInputElement
        ).value,
      ).toBe('10');
    });

    it('`groupHeader`, `editableItem`, and `nextSequence` are passed', async () => {
      wrapper = createWrapper();
      await nextTick();
      await wrapper.setProps({ groupHeader, editableItem: groupHeader });

      await wrapper
        .find('[data-cy=eth-deposit-event-form__advance] .accordion__header')
        .trigger('click');
      await nextTick();

      expect(
        (
          wrapper.find('[data-cy=validatorIndex] input')
            .element as HTMLInputElement
        ).value,
      ).toBe(groupHeader.validatorIndex.toString());

      expect(
        (wrapper.find('[data-cy=txHash] input').element as HTMLInputElement)
          .value,
      ).toBe(groupHeader.txHash);

      expect(
        (
          wrapper.find('[data-cy=eventIdentifier] input')
            .element as HTMLInputElement
        ).value,
      ).toBe(groupHeader.eventIdentifier);

      expect(
        (
          wrapper.find('[data-cy=depositor] .input-value')
            .element as HTMLInputElement
        ).value,
      ).toBe(groupHeader.locationLabel);

      expect(
        (wrapper.find('[data-cy=amount] input').element as HTMLInputElement)
          .value,
      ).toBe(groupHeader.balance.amount.toString());

      expect(
        (
          wrapper.find('[data-cy=sequenceIndex] input')
            .element as HTMLInputElement
        ).value.replace(',', ''),
      ).toBe(groupHeader.sequenceIndex.toString());
    });
  });
});
