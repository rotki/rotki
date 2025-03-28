import type { AssetMap } from '@/types/asset';
import type { EthDepositEvent } from '@/types/history/events';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import EthDepositEventForm from '@/modules/history/management/forms/EthDepositEventForm.vue';
import { useBalancePricesStore } from '@/store/balances/prices';
import { setupDayjs } from '@/utils/date';
import { bigNumberify, HistoryEventEntryType, One } from '@rotki/common';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('json-editor-vue', () => ({
  template: '<input />',
}));

vi.mock('@/store/balances/prices', () => ({
  useBalancePricesStore: vi.fn().mockReturnValue({
    getHistoricPrice: vi.fn(),
  }),
}));

describe('form/EthDepositEventForm.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof EthDepositEventForm>>;
  let pinia: Pinia;

  const asset = {
    assetType: 'own chain',
    isCustomAsset: false,
    name: 'Ethereum',
    symbol: 'ETH',
  };

  const mapping: AssetMap = {
    assetCollections: {},
    assets: { [asset.symbol]: asset },
  };

  const group: EthDepositEvent = {
    address: '0x00000000219ab540356cBB839Cbe05303d7705Fa',
    amount: bigNumberify('3.2'),
    asset: asset.symbol,
    counterparty: 'eth2',
    entryType: HistoryEventEntryType.ETH_DEPOSIT_EVENT,
    eventIdentifier: '10x3849ac4b278cac18f0e52a7d1a1dc1c14b1b4f50d6c11087e9a6591fd7b62d08',
    eventSubtype: 'deposit asset',
    eventType: 'staking',
    identifier: 11344,
    location: 'ethereum',
    locationLabel: '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
    notes: 'Deposit 3.2 ETH to validator 223',
    product: 'staking',
    sequenceIndex: 12,
    timestamp: 1697522243000,
    txHash: '0x3849ac4b278cac18f0e52a7d1a1dc1c14b1b4f50d6c11087e9a6591fd7b62d08',
    validatorIndex: 223,
  };

  beforeAll(() => {
    setupDayjs();
    pinia = createPinia();
    setActivePinia(pinia);
    vi.useFakeTimers();
  });

  beforeEach(() => {
    vi.mocked(useAssetInfoApi().assetMapping).mockResolvedValue(mapping);
    vi.mocked(useBalancePricesStore().getHistoricPrice).mockResolvedValue(One);
  });

  afterEach(() => {
    wrapper.unmount();
  });

  afterAll(() => {
    vi.useRealTimers();
  });

  const createWrapper = (options: ComponentMountingOptions<typeof EthDepositEventForm> = {
    props: {
      data: { nextSequenceId: '0', type: 'add' },
    },
  }): VueWrapper<InstanceType<typeof EthDepositEventForm>> =>
    mount(EthDepositEventForm, {
      global: {
        plugins: [pinia],
      },
      ...options,
    });

  describe('should prefill the fields based on the props', () => {
    it('should show the default state when adding a new event', async () => {
      wrapper = createWrapper();
      vi.advanceTimersToNextTimer();

      await wrapper.find('[data-cy=eth-deposit-event-form__advance] .accordion__header').trigger('click');
      vi.advanceTimersToNextTimer();

      expect((wrapper.find('[data-cy=validatorIndex] input').element as HTMLInputElement).value).toBe('');

      expect((wrapper.find('[data-cy=txHash] input').element as HTMLInputElement).value).toBe('');

      expect((wrapper.find('[data-cy=eventIdentifier] input').element as HTMLInputElement).value).toBe('');

      expect((wrapper.find('[data-cy=depositor] .input-value').element as HTMLInputElement).value).toBe('');

      expect((wrapper.find('[data-cy=sequenceIndex] input').element as HTMLInputElement).value).toBe('0');
    });

    it('should update when data adding a new event in a group', async () => {
      wrapper = createWrapper();
      vi.advanceTimersToNextTimer();
      await wrapper.setProps({ data: { group, nextSequenceId: '10', type: 'group-add' } });

      await wrapper.find('[data-cy=eth-deposit-event-form__advance] .accordion__header').trigger('click');
      vi.advanceTimersToNextTimer();

      expect((wrapper.find('[data-cy=validatorIndex] input').element as HTMLInputElement).value).toBe(
        group.validatorIndex.toString(),
      );

      expect((wrapper.find('[data-cy=txHash] input').element as HTMLInputElement).value).toBe(group.txHash);

      expect((wrapper.find('[data-cy=eventIdentifier] input').element as HTMLInputElement).value).toBe(
        group.eventIdentifier,
      );

      expect((wrapper.find('[data-cy=depositor] .input-value').element as HTMLInputElement).value).toBe(
        group.locationLabel,
      );

      expect((wrapper.find('[data-cy=amount] input').element as HTMLInputElement).value).toBe('0');

      expect((wrapper.find('[data-cy=sequenceIndex] input').element as HTMLInputElement).value).toBe('10');
    });

    it('it should update the fields when editing an event', async () => {
      wrapper = createWrapper();
      vi.advanceTimersToNextTimer();
      await wrapper.setProps({ data: { event: group, nextSequenceId: '1', type: 'edit' } });

      await wrapper.find('[data-cy=eth-deposit-event-form__advance] .accordion__header').trigger('click');
      vi.advanceTimersToNextTimer();

      expect((wrapper.find('[data-cy=validatorIndex] input').element as HTMLInputElement).value).toBe(
        group.validatorIndex.toString(),
      );

      expect((wrapper.find('[data-cy=txHash] input').element as HTMLInputElement).value).toBe(group.txHash);

      expect((wrapper.find('[data-cy=eventIdentifier] input').element as HTMLInputElement).value).toBe(
        group.eventIdentifier,
      );

      expect((wrapper.find('[data-cy=depositor] .input-value').element as HTMLInputElement).value).toBe(
        group.locationLabel,
      );

      expect((wrapper.find('[data-cy=amount] input').element as HTMLInputElement).value).toBe(
        group.amount.toString(),
      );

      expect((wrapper.find('[data-cy=sequenceIndex] input').element as HTMLInputElement).value.replace(',', '')).toBe(
        group.sequenceIndex.toString(),
      );
    });
  });
});
