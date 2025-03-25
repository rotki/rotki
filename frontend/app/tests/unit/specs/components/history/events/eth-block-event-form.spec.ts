import type { AssetMap } from '@/types/asset';
import type { EthBlockEvent } from '@/types/history/events';
import EthBlockEventForm from '@/components/history/events/forms/EthBlockEventForm.vue';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useBalancePricesStore } from '@/store/balances/prices';
import { setupDayjs } from '@/utils/date';
import { bigNumberify, HistoryEventEntryType, One } from '@rotki/common';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/store/balances/prices', () => ({
  useBalancePricesStore: vi.fn().mockReturnValue({
    getHistoricPrice: vi.fn(),
  }),
}));

describe('ethBlockEventForm.vue', () => {
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

  const groupHeader: EthBlockEvent = {
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
    notes: 'Validator 12 produced block 444 with 100 ETH going to 0x106B62Fdd27B748CF2Da3BacAB91a2CaBaeE6dCa as the mev reward',
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

  const createWrapper = (options: ComponentMountingOptions<typeof EthBlockEventForm> = {}) =>
    mount(EthBlockEventForm, {
      global: {
        plugins: [pinia],
      },
      ...options,
    });

  describe('should prefill the fields based on the props', () => {
    it('no `groupHeader`, nor `editableItem` are passed', async () => {
      wrapper = createWrapper();
      vi.advanceTimersToNextTimer();

      expect((wrapper.find('[data-cy=blockNumber] input').element as HTMLInputElement).value).toBe('');

      expect((wrapper.find('[data-cy=validatorIndex] input').element as HTMLInputElement).value).toBe('');

      expect((wrapper.find('[data-cy=feeRecipient] .input-value').element as HTMLInputElement).value).toBe('');

      expect((wrapper.find('[data-cy=isMevReward] input').element as HTMLInputElement).checked).toBeFalsy();
    });

    it('`groupHeader` are passed', async () => {
      wrapper = createWrapper();
      await wrapper.setProps({ groupHeader });
      await flushPromises();

      expect((wrapper.find('[data-cy=blockNumber] input').element as HTMLInputElement).value).toBe(groupHeader.blockNumber.toString());

      expect((wrapper.find('[data-cy=validatorIndex] input').element as HTMLInputElement).value).toBe(groupHeader.validatorIndex.toString());

      expect((wrapper.find('[data-cy=feeRecipient] .input-value').element as HTMLInputElement).value).toBe(groupHeader.locationLabel);

      expect((wrapper.find('[data-cy=amount] input').element as HTMLInputElement).value).toBe('0');

      expect((wrapper.find('[data-cy=isMevReward] input').element as HTMLInputElement).checked).toBeFalsy();
    });

    it('`groupHeader` and `editableItem` are passed', async () => {
      wrapper = createWrapper();
      await wrapper.setProps({ groupHeader, editableItem: groupHeader });
      await nextTick();
      await flushPromises();

      expect((wrapper.find('[data-cy=blockNumber] input').element as HTMLInputElement).value).toBe(groupHeader.blockNumber.toString());

      expect((wrapper.find('[data-cy=validatorIndex] input').element as HTMLInputElement).value).toBe(groupHeader.validatorIndex.toString());

      expect((wrapper.find('[data-cy=feeRecipient] .input-value').element as HTMLInputElement).value).toBe(groupHeader.locationLabel);

      expect((wrapper.find('[data-cy=amount] input').element as HTMLInputElement).value).toBe(groupHeader.amount.toString());

      expect((wrapper.find('[data-cy=isMevReward] input').element as HTMLInputElement).checked).toBeTruthy();
    });
  });
});
