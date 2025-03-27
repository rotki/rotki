import type { AssetMap } from '@/types/asset';
import type { EthBlockEvent } from '@/types/history/events';
import EthBlockEventForm from '@/components/history/events/forms/EthBlockEventForm.vue';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useBalancePricesStore } from '@/store/balances/prices';
import { setupDayjs } from '@/utils/date';
import { bigNumberify, HistoryEventEntryType, One } from '@rotki/common';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/store/balances/prices', () => ({
  useBalancePricesStore: vi.fn().mockReturnValue({
    getHistoricPrice: vi.fn(),
  }),
}));

describe('forms/EthBlockEventForm.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof EthBlockEventForm>>;
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

  const group: EthBlockEvent = {
    identifier: 11336,
    entryType: HistoryEventEntryType.ETH_BLOCK_EVENT,
    eventIdentifier: 'BP1_444',
    sequenceIndex: 0,
    timestamp: 1697442021000,
    location: 'ethereum',
    asset: asset.symbol,
    amount: bigNumberify('100'),
    eventType: 'staking',
    eventSubtype: 'mev reward',
    locationLabel: '0x106B62Fdd27B748CF2Da3BacAB91a2CaBaeE6dCa',
    notes:
      'Validator 12 produced block 444 with 100 ETH going to 0x106B62Fdd27B748CF2Da3BacAB91a2CaBaeE6dCa as the mev reward',
    validatorIndex: 122,
    blockNumber: 444,
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

  const createWrapper = (options: ComponentMountingOptions<typeof EthBlockEventForm> = {
    props: {
      data: { nextSequenceId: '0' },
    },
  }) =>
    mount(EthBlockEventForm, {
      global: {
        plugins: [pinia],
      },
      ...options,
    });

  describe('should prefill the fields based on the prop', () => {
    it('should show the default state when opening the form without any data', async () => {
      wrapper = createWrapper();
      vi.advanceTimersToNextTimer();

      expect((wrapper.find('[data-cy=blockNumber] input').element as HTMLInputElement).value).toBe('');

      expect((wrapper.find('[data-cy=validatorIndex] input').element as HTMLInputElement).value).toBe('');

      expect((wrapper.find('[data-cy=feeRecipient] .input-value').element as HTMLInputElement).value).toBe('');

      expect((wrapper.find('[data-cy=isMevReward] input').element as HTMLInputElement).checked).toBeFalsy();
    });

    it('should update the relevant fields when the `group` property is updated', async () => {
      wrapper = createWrapper();
      vi.advanceTimersToNextTimer();
      await wrapper.setProps({ data: { group } });

      expect((wrapper.find('[data-cy=blockNumber] input').element as HTMLInputElement).value).toBe(
        group.blockNumber.toString(),
      );

      expect((wrapper.find('[data-cy=validatorIndex] input').element as HTMLInputElement).value).toBe(
        group.validatorIndex.toString(),
      );

      expect((wrapper.find('[data-cy=feeRecipient] .input-value').element as HTMLInputElement).value).toBe(
        group.locationLabel,
      );

      expect((wrapper.find('[data-cy=amount] input').element as HTMLInputElement).value).toBe('0');

      expect((wrapper.find('[data-cy=isMevReward] input').element as HTMLInputElement).checked).toBeFalsy();
    });

    it('should update the fields when the `group` and `event` properties are updated', async () => {
      wrapper = createWrapper();
      vi.advanceTimersToNextTimer();
      await wrapper.setProps({ data: { group, event: group } });

      expect((wrapper.find('[data-cy=blockNumber] input').element as HTMLInputElement).value).toBe(
        group.blockNumber.toString(),
      );

      expect((wrapper.find('[data-cy=validatorIndex] input').element as HTMLInputElement).value).toBe(
        group.validatorIndex.toString(),
      );

      expect((wrapper.find('[data-cy=feeRecipient] .input-value').element as HTMLInputElement).value).toBe(
        group.locationLabel,
      );

      expect((wrapper.find('[data-cy=amount] input').element as HTMLInputElement).value).toBe(
        group.amount.toString(),
      );

      expect((wrapper.find('[data-cy=isMevReward] input').element as HTMLInputElement).checked).toBeTruthy();
    });
  });
});
